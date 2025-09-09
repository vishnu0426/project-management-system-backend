"""
Enhanced Project Endpoints
Organization-specific project management with proper filtering and access control
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Path, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.deps import get_current_active_user
from app.core.exceptions import ValidationError, ResourceNotFoundError, InsufficientPermissionsError
from app.models.user import User
from app.models.organization import OrganizationMember
from app.models.project import Project
from app.models.board import Board
from app.models.card import Card, CardAssignment
from app.schemas.project import ProjectCreate, ProjectUpdate, ProjectResponse, EnhancedProjectCreate, EnhancedProjectResponse
from app.services.organization_service import OrganizationService
from app.middleware.role_based_access import (
    require_permission, get_accessible_projects, RoleBasedAccessMiddleware
)
from app.services.enhanced_role_permissions import Permission
from app.services.email_service import email_service

router = APIRouter()


@router.get("/organization/{organization_id}", response_model=List[ProjectResponse])
async def get_organization_projects(
    organization_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get projects for specific organization with proper access control"""
    offset = (page - 1) * limit
    
    # Check organization access
    rbac = RoleBasedAccessMiddleware()
    has_access = await rbac.check_organization_access(
        str(current_user.id), organization_id, db
    )

    if not has_access:
        raise HTTPException(
            status_code=403,
            detail="Access denied to this organization"
        )
    
    # Get accessible projects based on user role
    accessible_project_ids = await get_accessible_projects(organization_id, current_user, db)
    
    if not accessible_project_ids:
        return []
    
    # Build query with filters
    query = select(Project).where(
        and_(
            Project.organization_id == organization_id,
            Project.id.in_(accessible_project_ids)
        )
    )
    
    # Apply filters
    if status:
        query = query.where(Project.status == status)
    if priority:
        query = query.where(Project.priority == priority)
    
    # Apply pagination and ordering
    query = query.offset(offset).limit(limit).order_by(Project.created_at.desc())
    
    result = await db.execute(query)
    projects = result.scalars().all()
    
    return [ProjectResponse.from_orm(project) for project in projects]


@router.get("/my-projects", response_model=List[ProjectResponse])
async def get_my_projects(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get projects assigned to current user across all organizations"""
    offset = (page - 1) * limit
    org_service = OrganizationService(db)
    
    # Get current organization
    current_org_id = await org_service.get_current_organization(str(current_user.id))
    if not current_org_id:
        return []
    
    # Get projects where user is assigned to cards
    result = await db.execute(
        select(Project)
        .join(Card, Card.project_id == Project.id)
        .join(CardAssignment, CardAssignment.card_id == Card.id)
        .where(
            and_(
                Project.organization_id == current_org_id,
                CardAssignment.user_id == current_user.id
            )
        )
        .distinct()
        .offset(offset)
        .limit(limit)
        .order_by(Project.updated_at.desc())
    )
    
    projects = result.scalars().all()
    return [ProjectResponse.from_orm(project) for project in projects]


@router.post("/organization/{organization_id}", response_model=ProjectResponse)
@require_permission(Permission.CREATE_PROJECT)
async def create_organization_project(
    organization_id: str,
    project_data: ProjectCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new project in specific organization"""
    # Verify organization access
    rbac = RoleBasedAccessMiddleware()
    has_access = await rbac.check_organization_access(
        str(current_user.id), organization_id, db
    )

    if not has_access:
        raise HTTPException(
            status_code=403,
            detail="Access denied to this organization"
        )

    # Get organization details for email
    org_result = await db.execute(
        select(OrganizationMember)
        .where(OrganizationMember.organization_id == organization_id)
        .where(OrganizationMember.user_id == current_user.id)
    )
    org_member = org_result.scalar_one_or_none()

    # Create project
    project = Project(
        organization_id=organization_id,
        name=project_data.name,
        description=project_data.description,
        status=project_data.status,
        priority=project_data.priority,
        start_date=project_data.start_date,
        due_date=project_data.due_date,
        created_by=current_user.id
    )

    db.add(project)
    await db.commit()
    await db.refresh(project)

    # Send project creation confirmation email
    if org_member and org_member.organization:
        project_email_data = {
            "name": project.name,
            "description": project.description,
            "status": project.status,
            "priority": project.priority,
            "start_date": project.start_date.isoformat() if project.start_date else None,
            "due_date": project.due_date.isoformat() if project.due_date else None,
            "created_at": project.created_at.isoformat() if project.created_at else None,
            "project_id": str(project.id)
        }

        background_tasks.add_task(
            email_service.send_project_creation_confirmation,
            current_user.email,
            f"{current_user.first_name} {current_user.last_name}",
            project_email_data,
            org_member.organization.name
        )

    return ProjectResponse.from_orm(project)


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get specific project with access control"""
    # Get project
    result = await db.execute(
        select(Project).where(Project.id == project_id)
    )
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Check project access
    rbac = RoleBasedAccessMiddleware()
    has_access = await rbac.check_project_access(
        str(current_user.id), project_id, str(project.organization_id), db
    )

    if not has_access:
        raise HTTPException(
            status_code=403,
            detail="Access denied to this project"
        )
    
    return ProjectResponse.from_orm(project)


@router.put("/{project_id}", response_model=ProjectResponse)
@require_permission(Permission.UPDATE_PROJECT, resource_param="project_id")
async def update_project(
    project_id: str,
    project_update: ProjectUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Update project with access control"""
    # Get project
    result = await db.execute(
        select(Project).where(Project.id == project_id)
    )
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Check project access
    rbac = RoleBasedAccessMiddleware()
    has_access = await rbac.check_project_access(
        str(current_user.id), project_id, str(project.organization_id), db
    )

    if not has_access:
        raise HTTPException(
            status_code=403,
            detail="Access denied to this project"
        )
    
    # Update project
    update_data = project_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(project, field, value)
    
    await db.commit()
    await db.refresh(project)
    
    return ProjectResponse.from_orm(project)


@router.delete("/{project_id}")
@require_permission(Permission.DELETE_PROJECT, resource_param="project_id")
async def delete_project(
    project_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete project with access control"""
    # Get project
    result = await db.execute(
        select(Project).where(Project.id == project_id)
    )
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Check project access
    rbac = RoleBasedAccessMiddleware()
    has_access = await rbac.check_project_access(
        str(current_user.id), project_id, str(project.organization_id), db
    )

    if not has_access:
        raise HTTPException(
            status_code=403,
            detail="Access denied to this project"
        )
    
    # Delete project (cascade will handle related records)
    await db.delete(project)
    await db.commit()
    
    return {"message": "Project deleted successfully"}


@router.get("/{project_id}/stats")
async def get_project_stats(
    project_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get project statistics with access control"""
    # Get project
    result = await db.execute(
        select(Project).where(Project.id == project_id)
    )
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Check project access
    rbac = RoleBasedAccessMiddleware()
    has_access = await rbac.check_project_access(
        str(current_user.id), project_id, str(project.organization_id), db
    )

    if not has_access:
        raise HTTPException(
            status_code=403,
            detail="Access denied to this project"
        )
    
    # Get statistics
    stats_result = await db.execute(
        select(
            func.count(Card.id).label('total_cards'),
            func.count(Card.id).filter(Card.status == 'completed').label('completed_cards'),
            func.count(Card.id).filter(Card.status == 'in_progress').label('in_progress_cards'),
            func.count(Card.id).filter(Card.status == 'todo').label('todo_cards'),
            func.count(Board.id).label('total_boards')
        )
        .select_from(Project)
        .outerjoin(Board, Board.project_id == Project.id)
        .outerjoin(Card, Card.board_id == Board.id)
        .where(Project.id == project_id)
        .group_by(Project.id)
    )
    
    stats = stats_result.first()
    
    if not stats:
        return {
            'total_cards': 0,
            'completed_cards': 0,
            'in_progress_cards': 0,
            'todo_cards': 0,
            'total_boards': 0,
            'completion_rate': 0.0
        }
    
    completion_rate = (stats.completed_cards / stats.total_cards * 100) if stats.total_cards > 0 else 0.0
    
    return {
        'total_cards': stats.total_cards or 0,
        'completed_cards': stats.completed_cards or 0,
        'in_progress_cards': stats.in_progress_cards or 0,
        'todo_cards': stats.todo_cards or 0,
        'total_boards': stats.total_boards or 0,
        'completion_rate': round(completion_rate, 2)
    }


@router.get("/organization/{organization_id}/dashboard")
async def get_organization_project_dashboard(
    organization_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get project dashboard for organization"""
    # Check organization access
    rbac = RoleBasedAccessMiddleware()
    has_access = await rbac.check_organization_access(
        str(current_user.id), organization_id, db
    )

    if not has_access:
        raise HTTPException(
            status_code=403,
            detail="Access denied to this organization"
        )

    # Get user permissions
    permissions = await rbac.get_dashboard_permissions(
        str(current_user.id), organization_id, db
    )
    
    # Get accessible projects
    accessible_project_ids = await get_accessible_projects(organization_id, current_user, db)
    
    # Get project statistics
    if accessible_project_ids:
        stats_result = await db.execute(
            select(
                func.count(Project.id).label('total_projects'),
                func.count(Project.id).filter(Project.status == 'active').label('active_projects'),
                func.count(Project.id).filter(Project.status == 'completed').label('completed_projects'),
                func.count(Project.id).filter(Project.status == 'on_hold').label('on_hold_projects')
            )
            .where(
                and_(
                    Project.organization_id == organization_id,
                    Project.id.in_(accessible_project_ids)
                )
            )
        )
        
        stats = stats_result.first()
    else:
        stats = None
    
    return {
        'permissions': permissions,
        'accessible_project_count': len(accessible_project_ids),
        'stats': {
            'total_projects': stats.total_projects if stats else 0,
            'active_projects': stats.active_projects if stats else 0,
            'completed_projects': stats.completed_projects if stats else 0,
            'on_hold_projects': stats.on_hold_projects if stats else 0
        }
    }
