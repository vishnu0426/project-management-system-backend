"""
Email Domain-Based Invitation Service
Handle organization domain-based email invitations with temporary passwords
"""
import secrets
import string
import smtplib
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

logger = logging.getLogger(__name__)

from app.models.user import User
from app.models.organization import Organization, OrganizationMember
from app.models.organization_settings import InvitationToken, OrganizationSettings
from app.models.project import Project
from app.models.notification import Notification
from app.core.security import hash_password, verify_password
from app.core.exceptions import ValidationError, ResourceNotFoundError
from app.config import settings
from app.services.email_service import email_service


class InvitationService:
    """Service for handling email invitations with domain validation"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def send_organization_invitation(
        self,
        email: str,
        organization_id: str,
        invited_role: str,
        inviter_id: str,
        project_id: Optional[str] = None,
        message: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send organization invitation with domain validation"""
        
        # Validate email domain
        await self._validate_email_domain(email, organization_id)
        
        # Check if user already exists
        existing_user = await self._get_user_by_email(email)
        if existing_user:
            # Check if already member
            existing_member = await self._get_organization_member(existing_user.id, organization_id)
            if existing_member:
                raise ValidationError("User is already a member of this organization")
        
        # Generate invitation token and temporary password
        token = self._generate_secure_token()
        temp_password = self._generate_temporary_password()
        
        # Create invitation record
        invitation = InvitationToken(
            token=token,
            email=email.lower().strip(),
            organization_id=organization_id,
            project_id=project_id,
            invited_role=invited_role,
            temporary_password=hash_password(temp_password),
            invited_by=inviter_id,
            invitation_message=message,
            expires_at=datetime.utcnow() + timedelta(days=7)
        )
        
        self.db.add(invitation)
        await self.db.commit()
        await self.db.refresh(invitation)
        
        # Get organization and inviter details
        org_details = await self._get_organization_details(organization_id)
        inviter_details = await self._get_user_details(inviter_id)
        project_details = await self._get_project_details(project_id) if project_id else None
        
        # Send invitation email
        email_sent = await self._send_invitation_email(
            email=email,
            token=token,
            temp_password=temp_password,
            organization=org_details,
            inviter=inviter_details,
            project=project_details,
            role=invited_role,
            message=message
        )

        # Create notification for the invited user (if they already exist in the system)
        existing_user = await self._get_user_by_email(email)
        if existing_user:
            notification = Notification(
                user_id=existing_user.id,
                organization_id=organization_id,
                title=f"Project Invitation from {org_details['name']}",
                message=f"You've been invited to join {org_details['name']} as a {invited_role}. Check your email for details.",
                type="team_invite",
                priority="normal",
                action_url=f"/accept-invitation?token={token}",
                notification_metadata={
                    'invitation_id': str(invitation.id),
                    'organization_name': org_details['name'],
                    'inviter_name': f"{inviter_details['first_name']} {inviter_details['last_name']}",
                    'role': invited_role,
                    'project_name': project_details['name'] if project_details else None
                }
            )
            self.db.add(notification)
            await self.db.commit()

        return {
            'invitation_id': str(invitation.id),
            'token': token,
            'temporary_password': temp_password,  # In production, don't return this
            'email_sent': email_sent,
            'expires_at': invitation.expires_at.isoformat()
        }
    
    async def accept_invitation(
        self,
        token: str,
        temp_password: str,
        new_password: str,
        first_name: str,
        last_name: str
    ) -> Dict[str, Any]:
        """Accept invitation and create/update user account"""
        
        # Get invitation
        invitation = await self._get_invitation_by_token(token)
        if not invitation:
            raise ValidationError("Invalid or expired invitation token")
        
        if invitation.is_used:
            raise ValidationError("Invitation has already been used")
        
        if invitation.expires_at < datetime.utcnow():
            raise ValidationError("Invitation has expired")
        
        # Verify temporary password
        if not verify_password(temp_password, invitation.temporary_password):
            raise ValidationError("Invalid temporary password")
        
        # Check if user already exists
        existing_user = await self._get_user_by_email(invitation.email)
        
        if existing_user:
            # Update existing user's password
            existing_user.hashed_password = hash_password(new_password)
            user = existing_user
        else:
            # Create new user
            user = User(
                email=invitation.email,
                first_name=first_name,
                last_name=last_name,
                hashed_password=hash_password(new_password),
                is_active=True,
                email_verified=True
            )
            self.db.add(user)
            await self.db.flush()  # Get user ID
        
        # Add user to organization
        existing_member = await self._get_organization_member(user.id, invitation.organization_id)
        if not existing_member:
            member = OrganizationMember(
                organization_id=invitation.organization_id,
                user_id=user.id,
                role=invitation.invited_role,
                invited_by=invitation.invited_by
            )
            self.db.add(member)
        
        # Mark invitation as used
        invitation.is_used = True
        invitation.used_at = datetime.utcnow()

        # Create welcome notification for the new member
        org_details = await self._get_organization_details(str(invitation.organization_id))
        welcome_notification = Notification(
            user_id=user.id,
            organization_id=invitation.organization_id,
            title=f"Welcome to {org_details['name']}!",
            message=f"You've successfully joined {org_details['name']} as a {invitation.invited_role}. Start exploring your new workspace!",
            type="team_invite_accepted",
            priority="normal",
            action_url="/dashboard",
            notification_metadata={
                'organization_name': org_details['name'],
                'role': invitation.invited_role,
                'project_id': str(invitation.project_id) if invitation.project_id else None
            }
        )
        self.db.add(welcome_notification)

        # Notify the inviter that invitation was accepted
        inviter_notification = Notification(
            user_id=invitation.invited_by,
            organization_id=invitation.organization_id,
            title="Invitation Accepted",
            message=f"{user.first_name} {user.last_name} ({invitation.email}) has joined {org_details['name']}",
            type="team_invite_accepted",
            priority="normal",
            action_url="/team-members",
            notification_metadata={
                'new_member_name': f"{user.first_name} {user.last_name}",
                'new_member_email': invitation.email,
                'role': invitation.invited_role,
                'organization_name': org_details['name']
            }
        )
        self.db.add(inviter_notification)

        await self.db.commit()

        return {
            'user_id': str(user.id),
            'organization_id': str(invitation.organization_id),
            'role': invitation.invited_role,
            'project_id': str(invitation.project_id) if invitation.project_id else None
        }
    
    async def get_pending_invitations(self, organization_id: str) -> list:
        """Get pending invitations for organization"""
        result = await self.db.execute(
            select(InvitationToken)
            .where(
                and_(
                    InvitationToken.organization_id == organization_id,
                    InvitationToken.is_used == False,
                    InvitationToken.expires_at > datetime.utcnow()
                )
            )
            .order_by(InvitationToken.created_at.desc())
        )
        
        invitations = result.scalars().all()
        return [
            {
                'id': str(inv.id),
                'email': inv.email,
                'role': inv.invited_role,
                'project_id': str(inv.project_id) if inv.project_id else None,
                'invited_by': str(inv.invited_by),
                'created_at': inv.created_at.isoformat(),
                'expires_at': inv.expires_at.isoformat()
            }
            for inv in invitations
        ]
    
    async def cancel_invitation(self, invitation_id: str, user_id: str) -> bool:
        """Cancel pending invitation"""
        result = await self.db.execute(
            select(InvitationToken)
            .where(
                and_(
                    InvitationToken.id == invitation_id,
                    InvitationToken.invited_by == user_id,
                    InvitationToken.is_used == False
                )
            )
        )
        
        invitation = result.scalar_one_or_none()
        if not invitation:
            return False
        
        await self.db.delete(invitation)
        await self.db.commit()
        return True
    
    async def _validate_email_domain(self, email: str, organization_id: str):
        """Validate email domain against organization settings"""
        email_domain = email.split('@')[1].lower()
        
        # Get organization settings
        settings_result = await self.db.execute(
            select(OrganizationSettings)
            .where(OrganizationSettings.organization_id == organization_id)
        )
        
        org_settings = settings_result.scalar_one_or_none()
        if not org_settings or not org_settings.require_domain_match:
            return  # No domain validation required
        
        # Get organization domain info
        org_result = await self.db.execute(
            select(Organization.domain, Organization.allowed_domains)
            .where(Organization.id == organization_id)
        )
        
        org_data = org_result.first()
        if not org_data:
            raise ValidationError("Organization not found")
        
        # Build allowed domains list
        allowed_domains = []
        if org_data.domain:
            allowed_domains.append(org_data.domain.lower())
        if org_data.allowed_domains:
            allowed_domains.extend([d.lower() for d in org_data.allowed_domains])
        if org_settings.allowed_invitation_domains:
            allowed_domains.extend([d.lower() for d in org_settings.allowed_invitation_domains])
        
        if allowed_domains and email_domain not in allowed_domains:
            raise ValidationError(
                f"Email domain '{email_domain}' is not allowed. "
                f"Allowed domains: {', '.join(allowed_domains)}"
            )
    
    async def _get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        result = await self.db.execute(
            select(User).where(User.email == email.lower())
        )
        return result.scalar_one_or_none()
    
    async def _get_organization_member(self, user_id: str, organization_id: str) -> Optional[OrganizationMember]:
        """Get organization member"""
        result = await self.db.execute(
            select(OrganizationMember)
            .where(
                and_(
                    OrganizationMember.user_id == user_id,
                    OrganizationMember.organization_id == organization_id
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def _get_invitation_by_token(self, token: str) -> Optional[InvitationToken]:
        """Get invitation by token"""
        result = await self.db.execute(
            select(InvitationToken).where(InvitationToken.token == token)
        )
        return result.scalar_one_or_none()
    
    async def _get_organization_details(self, organization_id: str) -> Dict[str, Any]:
        """Get organization details"""
        result = await self.db.execute(
            select(Organization).where(Organization.id == organization_id)
        )
        org = result.scalar_one_or_none()
        return {
            'id': str(org.id),
            'name': org.name,
            'description': org.description,
            'domain': org.domain
        } if org else {}
    
    async def _get_user_details(self, user_id: str) -> Dict[str, Any]:
        """Get user details"""
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        return {
            'id': str(user.id),
            'first_name': user.first_name,
            'last_name': user.last_name,
            'email': user.email
        } if user else {}
    
    async def _get_project_details(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Get project details"""
        result = await self.db.execute(
            select(Project).where(Project.id == project_id)
        )
        project = result.scalar_one_or_none()
        return {
            'id': str(project.id),
            'name': project.name,
            'description': project.description
        } if project else None
    
    async def _send_invitation_email(
        self,
        email: str,
        token: str,
        temp_password: str,
        organization: Dict[str, Any],
        inviter: Dict[str, Any],
        project: Optional[Dict[str, Any]],
        role: str,
        message: Optional[str]
    ) -> bool:
        """Send invitation email"""
        try:
            # Create invitation URL
            invitation_url = f"http://localhost:3000/accept-invitation?token={token}"

            # Send enhanced invitation email using centralized service
            return await email_service.send_enhanced_invitation_email(
                to_email=email,
                inviter_name=f"{inviter['first_name']} {inviter['last_name']}",
                organization_name=organization['name'],
                role=role,
                invitation_url=invitation_url,
                temp_password=temp_password,
                project_name=project['name'] if project else None,
                custom_message=message
            )

        except Exception as e:
            print(f"❌ Failed to send invitation email: {str(e)}")
            logger.error(f"Failed to send invitation email to {email}: {str(e)}")
            return False
    
    def _create_invitation_email_html(
        self,
        email: str,
        token: str,
        temp_password: str,
        organization: Dict[str, Any],
        inviter: Dict[str, Any],
        project: Optional[Dict[str, Any]],
        role: str,
        message: Optional[str]
    ) -> str:
        """Create HTML email body for invitation"""
        project_info = f"<p><strong>Project:</strong> {project['name']}</p>" if project else ""
        custom_message = f"<p><strong>Message from {inviter['first_name']}:</strong><br>{message}</p>" if message else ""
        
        return f"""
        <html>
        <body>
            <h2>You're invited to join {organization['name']}!</h2>
            
            <p>Hello,</p>
            
            <p>{inviter['first_name']} {inviter['last_name']} has invited you to join <strong>{organization['name']}</strong> as a <strong>{role}</strong>.</p>
            
            {project_info}
            {custom_message}
            
            <h3>Getting Started:</h3>
            <ol>
                <li>Click the link below to accept the invitation</li>
                <li>Use the temporary password provided to log in</li>
                <li>Set up your new password</li>
                <li>Start collaborating!</li>
            </ol>
            
            <p><strong>Invitation Token:</strong> {token}</p>
            <p><strong>Temporary Password:</strong> {temp_password}</p>
            
            <p><a href="{settings.FRONTEND_URL}/accept-invitation?token={token}" 
               style="background-color: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
               Accept Invitation
            </a></p>
            
            <p><small>This invitation will expire in 7 days.</small></p>
            
            <p>Best regards,<br>The {organization['name']} Team</p>
        </body>
        </html>
        """
    
    def _generate_secure_token(self) -> str:
        """Generate secure invitation token"""
        return secrets.token_urlsafe(32)
    
    def _generate_temporary_password(self) -> str:
        """Generate temporary password"""
        alphabet = string.ascii_letters + string.digits + "!@#$%"
        return ''.join(secrets.choice(alphabet) for _ in range(12))


# --- PATCH: Stronger domain validation override ---
async def _validate_email_domain(self, email: str, organization_id: str):
    """Validate email domain against organization & settings (patched)."""
    email_domain = email.split('@')[1].lower()

    # Load settings (may be None)
    settings_result = await self.db.execute(
        select(OrganizationSettings).where(OrganizationSettings.organization_id == organization_id)
    )
    org_settings = settings_result.scalar_one_or_none()

    # If settings explicitly disable domain matching, allow
    if org_settings and not org_settings.require_domain_match:
        return

    # Build allowed domains from Organization + Settings
    org_result = await self.db.execute(
        select(Organization.domain, Organization.allowed_domains).where(Organization.id == organization_id)
    )
    org_data = org_result.first()

    allowed_domains = []
    if org_data:
        if org_data.domain:
            allowed_domains.append(org_data.domain.lower())
        if org_data.allowed_domains:
            allowed_domains.extend([d.lower() for d in org_data.allowed_domains])

    if org_settings and getattr(org_settings, "allowed_invitation_domains", None):
        allowed_domains.extend([d.lower() for d in org_settings.allowed_invitation_domains])

    # If any allowed domains exist, enforce
    if allowed_domains and email_domain not in set(allowed_domains):
        raise ValidationError(
            f"Email domain '{email_domain}' is not allowed. Allowed domains: {', '.join(sorted(set(allowed_domains)))}"
        )
