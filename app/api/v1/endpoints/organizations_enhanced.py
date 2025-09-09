"""
Enhanced Organization Endpoints
Multi-organization management with role-based access control
"""
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

logger = logging.getLogger(__name__)

from app.core.database import get_db
from app.core.deps import get_current_active_user
from app.core.exceptions import ValidationError, ResourceNotFoundError, InsufficientPermissionsError
from app.models.user import User
from app.models.organization import Organization, OrganizationMember
from app.models.organization_settings import OrganizationSettings, UserOrganizationContext, InvitationToken
from app.models.project import Project
from app.services.organization_service import OrganizationService
from app.services.invitation_service import InvitationService
from app.schemas.organization import OrganizationCreate
from app.schemas.organization_enhanced import (
    OrganizationListResponse, EnhancedOrganizationResponse, OrganizationSwitchRequest,
    OrganizationSettingsCreate, OrganizationSettingsUpdate, OrganizationSettingsResponse,
    InvitationRequest, InvitationResponse, InvitationAcceptRequest,
    UserOrganizationContextResponse, DashboardPermissions
)

router = APIRouter()


@router.get("/enhanced", response_model=OrganizationListResponse)
async def get_enhanced_organizations(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all organizations for current user with enhanced information"""
    service = OrganizationService(db)
    
    # Get user's organizations with enhanced data
    org_data = await service.get_user_organizations(str(current_user.id))
    
    # Get current organization context
    current_org_id = await service.get_current_organization(str(current_user.id))
    
    # Format response
    organizations = []
    for data in org_data:
        org = data['organization']
        org_response = EnhancedOrganizationResponse(
            id=org.id,
            name=org.name,
            description=org.description,
            domain=org.domain,
            allowed_domains=org.allowed_domains,
            contact_email=org.contact_email,
            contact_phone=org.contact_phone,
            address_line1=org.address_line1,
            address_line2=org.address_line2,
            city=org.city,
            state=org.state,
            postal_code=org.postal_code,
            country=org.country,
            organization_category=org.organization_category,
            language=org.language,
            logo_url=org.logo_url,
            created_at=org.created_at,
            updated_at=org.updated_at,
            settings=org.settings,
            user_role=data['user_role'],
            permissions=data['permissions'],
            member_count=data['member_count'],
            project_count=data['project_count']
        )
        organizations.append(org_response)
    
    return OrganizationListResponse(
        organizations=organizations,
        current_organization_id=current_org_id,
        total_count=len(organizations)
    )


@router.post("/switch", response_model=UserOrganizationContextResponse)
async def switch_organization(
    request: OrganizationSwitchRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Switch user's current organization context"""
    service = OrganizationService(db)
    
    try:
        await service.switch_organization(str(current_user.id), str(request.organization_id))
        
        # Get updated context
        result = await db.execute(
            select(UserOrganizationContext)
            .where(UserOrganizationContext.user_id == current_user.id)
        )
        
        context = result.scalar_one()
        return context
        
    except InsufficientPermissionsError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.post("/enhanced", response_model=EnhancedOrganizationResponse)
async def create_enhanced_organization(
    org_data: OrganizationCreate,
    settings_data: Optional[OrganizationSettingsCreate] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create organization with enhanced settings"""
    service = OrganizationService(db)
    
    try:
        # Convert Pydantic models to dict
        org_dict = org_data.model_dump()
        settings_dict = settings_data.model_dump() if settings_data else None
        
        # Create organization with settings
        organization = await service.create_organization_with_settings(
            org_dict, str(current_user.id), settings_dict
        )
        
        # Get enhanced organization data
        org_data_list = await service.get_user_organizations(str(current_user.id))
        
        # Find the created organization
        for data in org_data_list:
            if data['organization'].id == organization.id:
                return EnhancedOrganizationResponse(
                    id=data['organization'].id,
                    name=data['organization'].name,
                    description=data['organization'].description,
                    domain=data['organization'].domain,
                    allowed_domains=data['organization'].allowed_domains,
                    contact_email=data['organization'].contact_email,
                    contact_phone=data['organization'].contact_phone,
                    address_line1=data['organization'].address_line1,
                    address_line2=data['organization'].address_line2,
                    city=data['organization'].city,
                    state=data['organization'].state,
                    postal_code=data['organization'].postal_code,
                    country=data['organization'].country,
                    organization_category=data['organization'].organization_category,
                    language=data['organization'].language,
                    logo_url=data['organization'].logo_url,
                    created_at=data['organization'].created_at,
                    updated_at=data['organization'].updated_at,
                    settings=data['organization'].settings,
                    user_role=data['user_role'],
                    permissions=data['permissions'],
                    member_count=data['member_count'],
                    project_count=data['project_count']
                )
        
        raise HTTPException(status_code=500, detail="Failed to retrieve created organization")
        
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{organization_id}/settings", response_model=OrganizationSettingsResponse)
async def get_organization_settings(
    organization_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get organization settings (admin/owner only)"""
    # Check if user is admin/owner of organization
    result = await db.execute(
        select(OrganizationMember.role)
        .where(
            and_(
                OrganizationMember.organization_id == organization_id,
                OrganizationMember.user_id == current_user.id,
                OrganizationMember.role.in_(['admin', 'owner'])
            )
        )
    )
    
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    # Get settings
    settings_result = await db.execute(
        select(OrganizationSettings)
        .where(OrganizationSettings.organization_id == organization_id)
    )
    
    settings = settings_result.scalar_one_or_none()
    if not settings:
        # Create default settings
        settings = OrganizationSettings(organization_id=organization_id)
        db.add(settings)
        await db.commit()
        await db.refresh(settings)
    
    return settings


@router.put("/{organization_id}/settings", response_model=OrganizationSettingsResponse)
async def update_organization_settings(
    organization_id: str,
    settings_update: OrganizationSettingsUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Update organization settings (owner only)"""
    # Check if user is owner of organization
    result = await db.execute(
        select(OrganizationMember.role)
        .where(
            and_(
                OrganizationMember.organization_id == organization_id,
                OrganizationMember.user_id == current_user.id,
                OrganizationMember.role == 'owner'
            )
        )
    )
    
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Only organization owners can update settings")
    
    # Get existing settings
    settings_result = await db.execute(
        select(OrganizationSettings)
        .where(OrganizationSettings.organization_id == organization_id)
    )
    
    settings = settings_result.scalar_one_or_none()
    if not settings:
        settings = OrganizationSettings(organization_id=organization_id)
        db.add(settings)
    
    # Update settings
    update_data = settings_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(settings, field, value)
    
    await db.commit()
    await db.refresh(settings)
    
    return settings


@router.post("/{organization_id}/invite", response_model=InvitationResponse)
async def invite_user_to_organization(
    organization_id: str,
    invitation: InvitationRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Invite user to organization (admin/owner only)"""
    logger.info(f"🚀 Invitation request: org_id={organization_id}, invitation={invitation.dict()}, user={current_user.email}")
    # Check if user can invite
    result = await db.execute(
        select(OrganizationMember.role)
        .where(
            and_(
                OrganizationMember.organization_id == organization_id,
                OrganizationMember.user_id == current_user.id,
                OrganizationMember.role.in_(['admin', 'owner'])
            )
        )
    )
    
    role = result.scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=403, detail="Insufficient permissions to invite users")
    
    # Admin can only invite members, owner can invite admin/members
    if role == 'admin' and invitation.role == 'admin':
        raise HTTPException(status_code=403, detail="Admins can only invite members")
    
    service = OrganizationService(db)
    
    try:
        invitation_token = await service.generate_invitation_token(
            email=invitation.email,
            organization_id=organization_id,
            invited_role=invitation.role,
            inviter_id=str(current_user.id),
            project_id=str(invitation.project_id) if invitation.project_id else None,
            message=invitation.invitation_message
        )
        
        # TODO: Send email with invitation details
        # background_tasks.add_task(send_invitation_email, invitation_token)
        
        return invitation_token
        
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{organization_id}/invite-enhanced", response_model=dict)
async def send_enhanced_invitation(
    organization_id: str,
    invitation: InvitationRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Send enhanced domain-based invitation with temporary password"""
    logger.info(f"🚀 Enhanced invitation request: org_id={organization_id}, invitation={invitation.dict()}, user={current_user.email}")
    # Check if user can invite
    result = await db.execute(
        select(OrganizationMember.role)
        .where(
            and_(
                OrganizationMember.organization_id == organization_id,
                OrganizationMember.user_id == current_user.id,
                OrganizationMember.role.in_(['admin', 'owner'])
            )
        )
    )

    role = result.scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=403, detail="Insufficient permissions to invite users")

    # Admin can only invite members, owner can invite admin/members
    if role == 'admin' and invitation.role == 'admin':
        raise HTTPException(status_code=403, detail="Admins can only invite members")

    invitation_service = InvitationService(db)

    try:
        result = await invitation_service.send_organization_invitation(
            email=invitation.email,
            organization_id=organization_id,
            invited_role=invitation.role,
            inviter_id=str(current_user.id),
            project_id=str(invitation.project_id) if invitation.project_id else None,
            message=invitation.invitation_message
        )

        return {
            'success': True,
            'message': f'Invitation sent to {invitation.email}',
            'invitation_id': result['invitation_id'],
            'expires_at': result['expires_at']
        }

    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/accept-invitation", response_model=dict)
async def accept_organization_invitation(
    invitation_data: InvitationAcceptRequest,
    db: AsyncSession = Depends(get_db)
):
    """Accept organization invitation and create/update user account"""
    invitation_service = InvitationService(db)

    try:
        result = await invitation_service.accept_invitation(
            token=invitation_data.token,
            temp_password=invitation_data.temporary_password,
            new_password=invitation_data.new_password,
            first_name=invitation_data.first_name,
            last_name=invitation_data.last_name
        )

        return {
            'success': True,
            'message': 'Invitation accepted successfully',
            'user_id': result['user_id'],
            'organization_id': result['organization_id'],
            'role': result['role']
        }

    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{organization_id}/invitations", response_model=list)
async def get_pending_invitations(
    organization_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get pending invitations for organization"""
    # Check if user is admin/owner
    result = await db.execute(
        select(OrganizationMember.role)
        .where(
            and_(
                OrganizationMember.organization_id == organization_id,
                OrganizationMember.user_id == current_user.id,
                OrganizationMember.role.in_(['admin', 'owner'])
            )
        )
    )

    if not result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    invitation_service = InvitationService(db)
    return await invitation_service.get_pending_invitations(organization_id)


@router.delete("/invitations/{invitation_id}")
async def cancel_invitation(
    invitation_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Cancel pending invitation"""
    invitation_service = InvitationService(db)

    success = await invitation_service.cancel_invitation(invitation_id, str(current_user.id))

    if not success:
        raise HTTPException(status_code=404, detail="Invitation not found or cannot be cancelled")

    return {'success': True, 'message': 'Invitation cancelled successfully'}
