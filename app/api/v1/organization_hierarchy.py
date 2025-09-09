"""
Organization hierarchy and collaboration API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from app.core.database import get_db
from app.core.deps import get_current_active_user
from app.models.user import User
from app.models.organization import Organization, OrganizationCollaboration, OrganizationMember
from app.schemas.organization import (
    OrganizationHierarchy, 
    OrganizationCollaborationCreate,
    OrganizationCollaborationResponse,
    OrganizationCollaborationUpdate
)

router = APIRouter()


@router.get("/organizations/{organization_id}/hierarchy", response_model=OrganizationHierarchy)
async def get_organization_hierarchy(
    organization_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get organization hierarchy including parent and children"""
    # Check if user has access to this organization
    member = db.query(OrganizationMember).filter(
        OrganizationMember.organization_id == organization_id,
        OrganizationMember.user_id == current_user.id
    ).first()
    
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to organization"
        )
    
    organization = db.query(Organization).filter(Organization.id == organization_id).first()
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    # Get parent organization
    parent = None
    if organization.parent_id:
        parent = db.query(Organization).filter(Organization.id == organization.parent_id).first()
    
    # Get child organizations
    children = db.query(Organization).filter(Organization.parent_id == organization_id).all()
    
    return OrganizationHierarchy(
        organization=organization,
        parent=parent,
        children=children,
        organization_type=organization.organization_type
    )


@router.put("/organizations/{organization_id}/parent/{parent_id}")
async def set_organization_parent(
    organization_id: UUID,
    parent_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Set parent organization for hierarchy"""
    # Check if user is owner/admin of the organization
    member = db.query(OrganizationMember).filter(
        OrganizationMember.organization_id == organization_id,
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.role.in_(['owner', 'admin'])
    ).first()
    
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owners and admins can modify organization hierarchy"
        )
    
    # Verify both organizations exist
    organization = db.query(Organization).filter(Organization.id == organization_id).first()
    parent_org = db.query(Organization).filter(Organization.id == parent_id).first()
    
    if not organization or not parent_org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    # Prevent circular hierarchy
    if parent_id == organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization cannot be its own parent"
        )
    
    # Update organization
    organization.parent_id = parent_id
    organization.organization_type = 'subsidiary'
    
    # Update parent to be parent type if not already
    if parent_org.organization_type == 'standard':
        parent_org.organization_type = 'parent'
    
    db.commit()
    db.refresh(organization)
    
    return {"message": "Organization hierarchy updated successfully"}


@router.delete("/organizations/{organization_id}/parent")
async def remove_organization_parent(
    organization_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Remove parent organization from hierarchy"""
    # Check if user is owner/admin of the organization
    member = db.query(OrganizationMember).filter(
        OrganizationMember.organization_id == organization_id,
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.role.in_(['owner', 'admin'])
    ).first()
    
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owners and admins can modify organization hierarchy"
        )
    
    organization = db.query(Organization).filter(Organization.id == organization_id).first()
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    organization.parent_id = None
    organization.organization_type = 'standard'
    db.commit()
    
    return {"message": "Organization removed from hierarchy"}


@router.get("/organizations/{organization_id}/collaborations", response_model=List[OrganizationCollaborationResponse])
async def get_organization_collaborations(
    organization_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all collaborations for an organization"""
    # Check if user has access to this organization
    member = db.query(OrganizationMember).filter(
        OrganizationMember.organization_id == organization_id,
        OrganizationMember.user_id == current_user.id
    ).first()
    
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to organization"
        )
    
    # Get collaborations where this org is either the main org or partner
    collaborations = db.query(OrganizationCollaboration).filter(
        (OrganizationCollaboration.organization_id == organization_id) |
        (OrganizationCollaboration.partner_organization_id == organization_id)
    ).all()
    
    return collaborations


@router.post("/organizations/{organization_id}/collaborations", response_model=OrganizationCollaborationResponse)
async def create_organization_collaboration(
    organization_id: UUID,
    collaboration_data: OrganizationCollaborationCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new organization collaboration"""
    # Check if user is owner/admin of the organization
    member = db.query(OrganizationMember).filter(
        OrganizationMember.organization_id == organization_id,
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.role.in_(['owner', 'admin'])
    ).first()
    
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owners and admins can create collaborations"
        )
    
    # Verify partner organization exists
    partner_org = db.query(Organization).filter(
        Organization.id == collaboration_data.partner_organization_id
    ).first()
    
    if not partner_org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Partner organization not found"
        )
    
    # Check if collaboration already exists
    existing = db.query(OrganizationCollaboration).filter(
        OrganizationCollaboration.organization_id == organization_id,
        OrganizationCollaboration.partner_organization_id == collaboration_data.partner_organization_id
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Collaboration already exists"
        )
    
    # Create collaboration
    collaboration = OrganizationCollaboration(
        organization_id=organization_id,
        partner_organization_id=collaboration_data.partner_organization_id,
        collaboration_type=collaboration_data.collaboration_type,
        permissions=collaboration_data.permissions,
        created_by=current_user.id
    )
    
    db.add(collaboration)
    db.commit()
    db.refresh(collaboration)
    
    return collaboration


@router.put("/organizations/{organization_id}/collaborations/{collaboration_id}")
async def update_organization_collaboration(
    organization_id: UUID,
    collaboration_id: UUID,
    collaboration_data: OrganizationCollaborationUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update organization collaboration status or settings"""
    # Check if user is owner/admin of either organization
    member = db.query(OrganizationMember).filter(
        OrganizationMember.organization_id == organization_id,
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.role.in_(['owner', 'admin'])
    ).first()
    
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owners and admins can update collaborations"
        )
    
    collaboration = db.query(OrganizationCollaboration).filter(
        OrganizationCollaboration.id == collaboration_id,
        (OrganizationCollaboration.organization_id == organization_id) |
        (OrganizationCollaboration.partner_organization_id == organization_id)
    ).first()
    
    if not collaboration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Collaboration not found"
        )
    
    # Update collaboration
    if collaboration_data.status:
        collaboration.status = collaboration_data.status
        if collaboration_data.status == 'active':
            collaboration.approved_by = current_user.id
            collaboration.approved_at = func.now()
    
    if collaboration_data.permissions:
        collaboration.permissions = collaboration_data.permissions
    
    if collaboration_data.expires_at:
        collaboration.expires_at = collaboration_data.expires_at
    
    db.commit()
    db.refresh(collaboration)
    
    return collaboration


@router.delete("/organizations/{organization_id}/collaborations/{collaboration_id}")
async def delete_organization_collaboration(
    organization_id: UUID,
    collaboration_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete organization collaboration"""
    # Check if user is owner/admin of the organization
    member = db.query(OrganizationMember).filter(
        OrganizationMember.organization_id == organization_id,
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.role.in_(['owner', 'admin'])
    ).first()
    
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owners and admins can delete collaborations"
        )
    
    collaboration = db.query(OrganizationCollaboration).filter(
        OrganizationCollaboration.id == collaboration_id,
        OrganizationCollaboration.organization_id == organization_id
    ).first()
    
    if not collaboration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Collaboration not found"
        )
    
    db.delete(collaboration)
    db.commit()
    
    return {"message": "Collaboration deleted successfully"}
