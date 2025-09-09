"""
Enhanced Organization Service
Multi-organization management with role-based access control
"""
import secrets
import string
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload

from app.models.user import User
from app.models.organization import Organization, OrganizationMember
from app.models.organization_settings import (
    OrganizationSettings, UserOrganizationContext, InvitationToken
)
from app.models.project import Project
from app.core.exceptions import ValidationError, ResourceNotFoundError, InsufficientPermissionsError
from app.core.security import hash_password, verify_password
from app.schemas.organization_enhanced import DashboardPermissions


class OrganizationService:
    """Enhanced organization management service"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_organizations(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all organizations for a user with enhanced information"""
        result = await self.db.execute(
            select(Organization, OrganizationMember.role)
            .join(OrganizationMember)
            .options(selectinload(Organization.settings))
            .where(OrganizationMember.user_id == user_id)
            .order_by(Organization.name)
        )
        
        organizations = []
        for org, role in result.all():
            # Get member and project counts
            member_count = await self._get_member_count(org.id)
            project_count = await self._get_project_count(org.id)
            
            # Get permissions for this user's role
            permissions = await self._get_user_permissions(org, role)
            
            organizations.append({
                'organization': org,
                'user_role': role,
                'permissions': permissions,
                'member_count': member_count,
                'project_count': project_count
            })
        
        return organizations

    async def switch_organization(self, user_id: str, organization_id: str) -> bool:
        """Switch user's current organization context"""
        # Verify user is member of the organization
        result = await self.db.execute(
            select(OrganizationMember)
            .where(
                and_(
                    OrganizationMember.user_id == user_id,
                    OrganizationMember.organization_id == organization_id
                )
            )
        )
        
        if not result.scalar_one_or_none():
            raise InsufficientPermissionsError("Not a member of this organization")
        
        # Update or create user context
        context_result = await self.db.execute(
            select(UserOrganizationContext)
            .where(UserOrganizationContext.user_id == user_id)
        )
        
        context = context_result.scalar_one_or_none()
        if context:
            context.current_organization_id = organization_id
            context.last_switched_at = datetime.utcnow()
        else:
            context = UserOrganizationContext(
                user_id=user_id,
                current_organization_id=organization_id
            )
            self.db.add(context)
        
        await self.db.commit()
        return True

    async def get_current_organization(self, user_id: str) -> Optional[str]:
        """Get user's current organization context"""
        result = await self.db.execute(
            select(UserOrganizationContext.current_organization_id)
            .where(UserOrganizationContext.user_id == user_id)
        )
        
        org_id = result.scalar_one_or_none()
        if org_id:
            # Verify user is still member of this organization
            member_result = await self.db.execute(
                select(OrganizationMember)
                .where(
                    and_(
                        OrganizationMember.user_id == user_id,
                        OrganizationMember.organization_id == org_id
                    )
                )
            )
            
            if member_result.scalar_one_or_none():
                return str(org_id)
        
        # If no valid context, return first organization
        first_org_result = await self.db.execute(
            select(OrganizationMember.organization_id)
            .where(OrganizationMember.user_id == user_id)
            .limit(1)
        )
        
        first_org = first_org_result.scalar_one_or_none()
        if first_org:
            await self.switch_organization(user_id, str(first_org))
            return str(first_org)
        
        return None

    async def create_organization_with_settings(
        self, 
        org_data: Dict[str, Any], 
        creator_id: str,
        settings_data: Optional[Dict[str, Any]] = None
    ) -> Organization:
        """Create organization with default settings"""
        # Create organization
        organization = Organization(
            name=org_data['name'],
            description=org_data.get('description'),
            domain=org_data.get('domain'),
            allowed_domains=org_data.get('allowed_domains'),
            contact_email=org_data.get('contact_email'),
            contact_phone=org_data.get('contact_phone'),
            address_line1=org_data.get('address_line1'),
            address_line2=org_data.get('address_line2'),
            city=org_data.get('city'),
            state=org_data.get('state'),
            postal_code=org_data.get('postal_code'),
            country=org_data.get('country'),
            organization_category=org_data.get('organization_category'),
            language=org_data.get('language'),
            created_by=creator_id
        )
        
        self.db.add(organization)
        await self.db.flush()  # Get the organization ID
        
        # Create organization settings
        settings = OrganizationSettings(
            organization_id=organization.id,
            **(settings_data or {})
        )
        self.db.add(settings)
        
        # Add creator as owner
        member = OrganizationMember(
            organization_id=organization.id,
            user_id=creator_id,
            role='owner',
            invited_by=creator_id
        )
        self.db.add(member)
        
        await self.db.commit()
        await self.db.refresh(organization)
        
        return organization

    async def generate_invitation_token(
        self,
        email: str,
        organization_id: str,
        invited_role: str,
        inviter_id: str,
        project_id: Optional[str] = None,
        message: Optional[str] = None
    ) -> InvitationToken:
        """Generate invitation token with temporary password"""
        # Check if organization allows this invitation
        org_settings = await self._get_organization_settings(organization_id)
        
        if org_settings.require_domain_match:
            email_domain = email.split('@')[1].lower()
            allowed_domains = org_settings.allowed_invitation_domains or []
            
            # Get organization domain
            org_result = await self.db.execute(
                select(Organization.domain, Organization.allowed_domains)
                .where(Organization.id == organization_id)
            )
            org_data = org_result.first()
            
            if org_data and org_data.domain:
                allowed_domains.append(org_data.domain.lower())
            if org_data and org_data.allowed_domains:
                allowed_domains.extend([d.lower() for d in org_data.allowed_domains])
            
            if allowed_domains and email_domain not in allowed_domains:
                raise ValidationError(f"Email domain {email_domain} is not allowed for this organization")
        
        # Generate token and temporary password
        token = self._generate_secure_token()
        temp_password = self._generate_temporary_password()
        
        # Create invitation
        invitation = InvitationToken(
            token=token,
            email=email.lower().strip(),
            organization_id=organization_id,
            project_id=project_id,
            invited_role=invited_role,
            temporary_password=hash_password(temp_password),
            invited_by=inviter_id,
            invitation_message=message,
            expires_at=datetime.utcnow() + timedelta(days=7)  # 7 days expiry
        )
        
        self.db.add(invitation)
        await self.db.commit()
        
        # Store plain temporary password for email (in real app, send via email)
        invitation.plain_temp_password = temp_password
        
        return invitation

    async def _get_member_count(self, organization_id: str) -> int:
        """Get member count for organization"""
        result = await self.db.execute(
            select(func.count(OrganizationMember.id))
            .where(OrganizationMember.organization_id == organization_id)
        )
        return result.scalar() or 0

    async def _get_project_count(self, organization_id: str) -> int:
        """Get project count for organization"""
        result = await self.db.execute(
            select(func.count(Project.id))
            .where(Project.organization_id == organization_id)
        )
        return result.scalar() or 0

    async def _get_user_permissions(self, organization: Organization, role: str) -> DashboardPermissions:
        """Get user permissions based on role and organization settings"""
        settings = organization.settings
        
        if role == 'owner':
            return DashboardPermissions(
                can_create_projects=True,
                can_schedule_meetings=True,
                can_invite_members=True,
                can_change_roles=True,
                can_view_all_projects=True,
                can_manage_organization=True
            )
        elif role == 'admin':
            return DashboardPermissions(
                can_create_projects=settings.allow_admin_create_projects if settings else True,
                can_schedule_meetings=settings.allow_admin_schedule_meetings if settings else True,
                can_invite_members=True,
                can_change_roles=True,  # Can promote to member only
                can_view_all_projects=True,
                can_manage_organization=False
            )
        elif role == 'member':
            return DashboardPermissions(
                can_create_projects=settings.allow_member_create_projects if settings else False,
                can_schedule_meetings=settings.allow_member_schedule_meetings if settings else False,
                can_invite_members=False,
                can_change_roles=False,
                can_view_all_projects=False,  # Only assigned projects
                can_manage_organization=False
            )
        else:  # viewer
            return DashboardPermissions(
                can_create_projects=False,
                can_schedule_meetings=False,
                can_invite_members=False,
                can_change_roles=False,
                can_view_all_projects=False,
                can_manage_organization=False
            )

    async def _get_organization_settings(self, organization_id: str) -> OrganizationSettings:
        """Get organization settings"""
        result = await self.db.execute(
            select(OrganizationSettings)
            .where(OrganizationSettings.organization_id == organization_id)
        )
        
        settings = result.scalar_one_or_none()
        if not settings:
            # Create default settings
            settings = OrganizationSettings(organization_id=organization_id)
            self.db.add(settings)
            await self.db.commit()
        
        return settings

    def _generate_secure_token(self) -> str:
        """Generate secure invitation token"""
        return secrets.token_urlsafe(32)

    def _generate_temporary_password(self) -> str:
        """Generate temporary password"""
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(12))
