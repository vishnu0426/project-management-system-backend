"""
Team management endpoints
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from pydantic import BaseModel

from app.core.database import get_db
from app.core.deps import get_current_active_user, require_admin, require_member, require_member_by_path, require_admin_by_path
from app.core.exceptions import ResourceNotFoundError, InsufficientPermissionsError, ValidationError
from app.models.user import User
from app.models.organization import OrganizationMember
from app.schemas.organization import OrganizationMemberResponse


class BulkActionRequest(BaseModel):
    action: str
    member_ids: List[str]
    new_role: Optional[str] = None

router = APIRouter()


@router.get("", response_model=List[dict])
async def get_teams(
    organization_id: str = Query(..., description="Organization ID to filter teams"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all teams for an organization"""
    # Check organization membership
    org_member_result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.user_id == current_user.id
        )
    )
    if not org_member_result.scalar_one_or_none():
        raise InsufficientPermissionsError("Access denied")

    # Mock teams data for now
    teams = [
        {
            "id": "team-1",
            "name": "Development Team",
            "description": "Frontend and backend developers",
            "member_count": 8,
            "organization_id": organization_id
        },
        {
            "id": "team-2",
            "name": "Design Team",
            "description": "UI/UX designers and researchers",
            "member_count": 4,
            "organization_id": organization_id
        }
    ]

    return teams


@router.post("", response_model=dict)
async def create_team(
    team_data: dict,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new team"""
    # Mock team creation
    team = {
        "id": f"team-{len(team_data.get('name', 'new'))}",
        "name": team_data.get("name", "New Team"),
        "description": team_data.get("description", ""),
        "member_count": 1,
        "organization_id": team_data.get("organization_id"),
        "created_by": str(current_user.id)
    }

    return team


@router.get("/{team_id}", response_model=dict)
async def get_team(
    team_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get team by ID"""
    # Mock team data
    team = {
        "id": team_id,
        "name": "Development Team",
        "description": "Frontend and backend developers",
        "member_count": 8,
        "members": [
            {
                "id": str(current_user.id),
                "email": current_user.email,
                "first_name": current_user.first_name,
                "last_name": current_user.last_name,
                "role": "member"
            }
        ],
        "created_at": "2025-08-01T00:00:00Z",
        "updated_at": "2025-08-03T00:00:00Z"
    }

    return team


@router.get("/{organization_id}/members", response_model=List[OrganizationMemberResponse])
async def get_team_members(
    organization_id: str,
    search: Optional[str] = Query(None),
    role: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    org_member: OrganizationMember = Depends(require_member_by_path),
    db: AsyncSession = Depends(get_db)
):
    """Get team members with search and filters"""
    offset = (page - 1) * limit
    
    query = select(OrganizationMember).options(
        selectinload(OrganizationMember.user)
    ).where(OrganizationMember.organization_id == organization_id)
    
    # Apply filters
    if role:
        query = query.where(OrganizationMember.role == role)
    
    if search:
        # Search in user's name and email
        query = query.join(User).where(
            (User.first_name.ilike(f"%{search}%")) |
            (User.last_name.ilike(f"%{search}%")) |
            (User.email.ilike(f"%{search}%"))
        )
    
    query = query.offset(offset).limit(limit).order_by(OrganizationMember.joined_at)
    
    result = await db.execute(query)
    members = result.scalars().all()
    
    # Format response
    response = []
    for member in members:
        member_data = OrganizationMemberResponse(
            id=str(member.id),
            user_id=str(member.user_id),
            role=member.role,
            joined_at=member.joined_at,
            user={
                "id": str(member.user.id),
                "email": member.user.email,
                "first_name": member.user.first_name,
                "last_name": member.user.last_name,
                "avatar_url": member.user.avatar_url
            }
        )
        response.append(member_data)
    
    return response


@router.get("/{organization_id}/members/{user_id}/activity")
async def get_member_activity(
    organization_id: str,
    user_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    org_member: OrganizationMember = Depends(require_member_by_path),
    db: AsyncSession = Depends(get_db)
):
    """Get activity for a team member"""
    # Check if target user is member of organization
    target_member_result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.user_id == user_id
        )
    )
    if not target_member_result.scalar_one_or_none():
        raise ResourceNotFoundError("User is not a member of this organization")
    
    # TODO: Get activity logs from database
    # For now, return empty list
    return {
        "success": True,
        "data": {
            "items": [],
            "pagination": {
                "page": page,
                "limit": limit,
                "total": 0,
                "totalPages": 0,
                "hasNext": False,
                "hasPrev": False
            }
        }
    }


@router.post("/{organization_id}/members/bulk-action")
async def bulk_member_action(
    organization_id: str,
    bulk_request: BulkActionRequest,
    current_user: User = Depends(get_current_active_user),
    org_member: OrganizationMember = Depends(require_admin_by_path),
    db: AsyncSession = Depends(get_db)
):
    """Perform bulk actions on team members"""
    if bulk_request.action not in ['remove', 'change_role']:
        raise ValidationError("Invalid action. Must be 'remove' or 'change_role'")
    
    # TODO: Implement bulk actions
    # For now, just return success
    return {
        "success": True,
        "message": f"Bulk action '{bulk_request.action}' completed for {len(bulk_request.member_ids)} members"
    }


# -----------------------------------------------------------------------------
# Team statistics
#
# The front‑end calls `GET /api/v1/teams/{organization_id}/stats` to display
# summary information about an organization’s team members.  Prior to
# this implementation the endpoint was missing, resulting in a 404.  The
# handler below performs a simple membership count and role breakdown for
# the specified organization.  Only members of the organization can
# access these statistics.

@router.get("/{organization_id}/stats")
async def get_team_stats(
    organization_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Return high‑level statistics about an organization's team.

    The stats include the total number of members and a breakdown of
    how many members hold each role (viewer, member, admin, owner).
    Only users who belong to the organization may access these stats.
    """
    # Verify that the requesting user is a member of the organization.
    membership_result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.user_id == current_user.id,
        )
    )
    if not membership_result.scalar_one_or_none():
        raise InsufficientPermissionsError("Access denied")

    # Count total members and group counts by role.
    count_query = (
        select(OrganizationMember.role, func.count())
        .where(OrganizationMember.organization_id == organization_id)
        .group_by(OrganizationMember.role)
    )
    result = await db.execute(count_query)
    role_counts = {role: count for role, count in result.all()}
    total_members = sum(role_counts.values())

    # Provide a default of zero for any roles that may not be present.
    for role in ["viewer", "member", "admin", "owner"]:
        role_counts.setdefault(role, 0)

    return {
        "success": True,
        "data": {
            "total_members": total_members,
            "role_counts": role_counts,
        },
        "message": "Team statistics retrieved successfully",
    }
