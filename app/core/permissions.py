"""
Role-based permission checking utilities
"""
from typing import Optional
from fastapi import HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.deps import get_current_active_user
from app.models.user import User
from app.models.organization import OrganizationMember
from app.models.project import Project
from app.models.board import Board
from app.models.column import Column


class PermissionError(HTTPException):
    def __init__(self, detail: str = "Insufficient permissions"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail
        )


async def get_user_role_in_organization(
    user_id: str, 
    organization_id: str, 
    db: AsyncSession
) -> Optional[str]:
    """Get user's role in a specific organization"""
    result = await db.execute(
        select(OrganizationMember.role).where(
            OrganizationMember.user_id == user_id,
            OrganizationMember.organization_id == organization_id
        )
    )
    role = result.scalar_one_or_none()
    return role


async def get_user_role_for_project(
    user_id: str, 
    project_id: str, 
    db: AsyncSession
) -> Optional[str]:
    """Get user's role for a specific project (via organization)"""
    result = await db.execute(
        select(Project.organization_id).where(Project.id == project_id)
    )
    organization_id = result.scalar_one_or_none()
    
    if not organization_id:
        return None
    
    return await get_user_role_in_organization(user_id, organization_id, db)


async def get_user_role_for_board(
    user_id: str, 
    board_id: str, 
    db: AsyncSession
) -> Optional[str]:
    """Get user's role for a specific board (via project -> organization)"""
    result = await db.execute(
        select(Project.organization_id)
        .join(Board, Board.project_id == Project.id)
        .where(Board.id == board_id)
    )
    organization_id = result.scalar_one_or_none()
    
    if not organization_id:
        return None
    
    return await get_user_role_in_organization(user_id, organization_id, db)


async def get_user_role_for_column(
    user_id: str, 
    column_id: str, 
    db: AsyncSession
) -> Optional[str]:
    """Get user's role for a specific column (via board -> project -> organization)"""
    result = await db.execute(
        select(Project.organization_id)
        .join(Board, Board.project_id == Project.id)
        .join(Column, Column.board_id == Board.id)
        .where(Column.id == column_id)
    )
    organization_id = result.scalar_one_or_none()
    
    if not organization_id:
        return None
    
    return await get_user_role_in_organization(user_id, organization_id, db)


def can_create_projects(role: str) -> bool:
    """Check if role can create projects"""
    return role in ["owner", "admin", "member"]


def can_edit_projects(role: str) -> bool:
    """Check if role can edit projects"""
    return role in ["owner", "admin", "member"]


def can_delete_projects(role: str) -> bool:
    """Check if role can delete projects"""
    return role in ["owner", "admin"]


def can_create_boards(role: str) -> bool:
    """Check if role can create boards"""
    return role in ["owner", "admin", "member"]


def can_edit_boards(role: str) -> bool:
    """Check if role can edit boards"""
    return role in ["owner", "admin", "member"]


def can_delete_boards(role: str) -> bool:
    """Check if role can delete boards"""
    return role in ["owner", "admin"]


def can_create_cards(role: str) -> bool:
    """Check if role can create cards"""
    return role in ["owner", "admin", "member"]


def can_edit_cards(role: str) -> bool:
    """Check if role can edit cards"""
    return role in ["owner", "admin", "member"]


def can_delete_cards(role: str) -> bool:
    """Check if role can delete cards"""
    return role in ["owner", "admin", "member"]


def can_manage_members(role: str) -> bool:
    """Check if role can manage organization members"""
    return role in ["owner", "admin"]


def can_view_analytics(role: str) -> bool:
    """Check if role can view analytics"""
    return role in ["owner", "admin", "member", "viewer"]


def can_manage_organization(role: str) -> bool:
    """Check if role can manage organization settings"""
    return role in ["owner"]


async def require_permission_for_organization(
    organization_id: str,
    permission_check: callable,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Dependency to require specific permission for organization"""
    role = await get_user_role_in_organization(current_user.id, organization_id, db)
    
    if not role:
        raise PermissionError("User is not a member of this organization")
    
    if not permission_check(role):
        raise PermissionError(f"Role '{role}' does not have required permission")
    
    return role


async def require_permission_for_project(
    project_id: str,
    permission_check: callable,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Dependency to require specific permission for project"""
    role = await get_user_role_for_project(current_user.id, project_id, db)
    
    if not role:
        raise PermissionError("User does not have access to this project")
    
    if not permission_check(role):
        raise PermissionError(f"Role '{role}' does not have required permission")
    
    return role


async def require_permission_for_column(
    column_id: str,
    permission_check: callable,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Dependency to require specific permission for column"""
    role = await get_user_role_for_column(current_user.id, column_id, db)
    
    if not role:
        raise PermissionError("User does not have access to this column")
    
    if not permission_check(role):
        raise PermissionError(f"Role '{role}' does not have required permission")
    
    return role
