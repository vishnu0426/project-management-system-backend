"""
Role-Specific Dashboard API Endpoints
Backend endpoints to support existing frontend role-based dashboards
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.deps import get_current_active_user
from app.models.user import User
from app.models.organization import Organization, OrganizationMember
from app.models.project import Project
from app.models.board import Board
from app.models.column import Column
from app.models.card import Card, CardAssignment
from app.models.organization_settings import MeetingSchedule
from app.services.organization_service import OrganizationService
from app.middleware.role_based_access import get_accessible_projects

router = APIRouter()


@router.get("/stats")
async def get_dashboard_stats(
    organization_id: Optional[str] = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get dashboard stats - routes to appropriate role-based dashboard"""
    org_service = OrganizationService(db)

    # Get current organization if not specified
    if not organization_id:
        organization_id = await org_service.get_current_organization(str(current_user.id))
        if not organization_id:
            raise HTTPException(status_code=400, detail="No organization context")

    # Get user's role in the organization
    result = await db.execute(
        select(OrganizationMember.role)
        .where(
            and_(
                OrganizationMember.user_id == current_user.id,
                OrganizationMember.organization_id == organization_id
            )
        )
    )

    role = result.scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=403, detail="Organization access required")

    # Route to appropriate dashboard based on role
    if role == 'owner':
        return await get_owner_dashboard(organization_id, current_user, db)
    elif role == 'admin':
        return await get_admin_dashboard(organization_id, current_user, db)
    elif role == 'member':
        return await get_member_dashboard(organization_id, current_user, db)
    elif role == 'viewer':
        return await get_viewer_dashboard(organization_id, current_user, db)
    else:
        raise HTTPException(status_code=403, detail="Invalid role")


@router.get("/owner-dashboard")
async def get_owner_dashboard(
    organization_id: Optional[str] = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get owner dashboard data"""
    org_service = OrganizationService(db)
    
    # Get current organization if not specified
    if not organization_id:
        organization_id = await org_service.get_current_organization(str(current_user.id))
        if not organization_id:
            raise HTTPException(status_code=400, detail="No organization context")
    
    # Verify user is owner
    result = await db.execute(
        select(OrganizationMember.role)
        .where(
            and_(
                OrganizationMember.user_id == current_user.id,
                OrganizationMember.organization_id == organization_id,
                OrganizationMember.role == 'owner'
            )
        )
    )
    
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Owner access required")
    
    # Get comprehensive statistics
    stats_result = await db.execute(
        select(
            func.count(Project.id.distinct()).label('total_projects'),
            func.count(OrganizationMember.id.distinct()).label('total_members'),
            func.count(Card.id.distinct()).label('total_tasks'),
            func.count(Card.id.distinct()).filter(
                func.lower(Column.name).in_(['done', 'completed', 'finished'])
            ).label('completed_tasks'),
            func.count(MeetingSchedule.id.distinct()).label('total_meetings')
        )
        .select_from(Organization)
        .outerjoin(Project, Project.organization_id == Organization.id)
        .outerjoin(OrganizationMember, OrganizationMember.organization_id == Organization.id)
        .outerjoin(Board, Board.project_id == Project.id)
        .outerjoin(Column, Column.board_id == Board.id)
        .outerjoin(Card, Card.column_id == Column.id)
        .outerjoin(MeetingSchedule, MeetingSchedule.organization_id == Organization.id)
        .where(Organization.id == organization_id)
        .group_by(Organization.id)
    )
    
    stats = stats_result.first()
    
    # Get recent projects
    recent_projects_result = await db.execute(
        select(Project)
        .where(Project.organization_id == organization_id)
        .order_by(Project.created_at.desc())
        .limit(5)
    )
    recent_projects = recent_projects_result.scalars().all()
    
    # Get organization members by role
    members_result = await db.execute(
        select(
            OrganizationMember.role,
            func.count(OrganizationMember.id).label('count')
        )
        .where(OrganizationMember.organization_id == organization_id)
        .group_by(OrganizationMember.role)
    )
    
    role_distribution = {row.role: row.count for row in members_result.all()}
    
    return {
        'role': 'owner',
        'organization_id': organization_id,
        'stats': {
            'total_projects': stats.total_projects if stats else 0,
            'total_members': stats.total_members if stats else 0,
            'total_tasks': stats.total_tasks if stats else 0,
            'completed_tasks': stats.completed_tasks if stats else 0,
            'total_meetings': stats.total_meetings if stats else 0,
            'completion_rate': round((stats.completed_tasks / stats.total_tasks * 100) if stats and stats.total_tasks > 0 else 0, 2)
        },
        'recent_projects': [
            {
                'id': str(p.id),
                'name': p.name,
                'status': p.status,
                'created_at': p.created_at.isoformat()
            } for p in recent_projects
        ],
        'role_distribution': role_distribution,
        'permissions': {
            'can_create_projects': True,
            'can_invite_members': True,
            'can_manage_organization': True,
            'can_schedule_meetings': True,
            'can_view_all_data': True
        }
    }


@router.get("/admin-dashboard")
async def get_admin_dashboard(
    organization_id: Optional[str] = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get admin dashboard data"""
    org_service = OrganizationService(db)
    
    # Get current organization if not specified
    if not organization_id:
        organization_id = await org_service.get_current_organization(str(current_user.id))
        if not organization_id:
            raise HTTPException(status_code=400, detail="No organization context")
    
    # Verify user is admin
    result = await db.execute(
        select(OrganizationMember.role)
        .where(
            and_(
                OrganizationMember.user_id == current_user.id,
                OrganizationMember.organization_id == organization_id,
                OrganizationMember.role.in_(['admin', 'owner'])
            )
        )
    )
    
    role = result.scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Get accessible projects
    accessible_project_ids = await get_accessible_projects(organization_id, current_user, db)
    
    # Get project statistics
    if accessible_project_ids:
        stats_result = await db.execute(
            select(
                func.count(Project.id.distinct()).label('accessible_projects'),
                func.count(Card.id.distinct()).label('total_tasks'),
                func.count(Card.id.distinct()).filter(Card.status == 'completed').label('completed_tasks'),
                func.count(Card.id.distinct()).filter(CardAssignment.user_id == current_user.id).label('my_tasks')
            )
            .select_from(Project)
            .outerjoin(Board, Board.project_id == Project.id)
            .outerjoin(Card, Card.board_id == Board.id)
            .outerjoin(CardAssignment, CardAssignment.card_id == Card.id)
            .where(Project.id.in_(accessible_project_ids))
        )
        
        stats = stats_result.first()
    else:
        stats = None

    # Get organization member count
    member_count_result = await db.execute(
        select(func.count(OrganizationMember.id))
        .where(OrganizationMember.organization_id == organization_id)
    )
    total_members = member_count_result.scalar() or 0

    # Get recent tasks assigned to admin
    recent_tasks_result = await db.execute(
        select(Card)
        .join(CardAssignment, CardAssignment.card_id == Card.id)
        .join(Board, Board.id == Card.board_id)
        .join(Project, Project.id == Board.project_id)
        .where(
            and_(
                CardAssignment.user_id == current_user.id,
                Project.organization_id == organization_id
            )
        )
        .order_by(Card.updated_at.desc())
        .limit(5)
    )
    recent_tasks = recent_tasks_result.scalars().all()
    
    return {
        'role': role,
        'organization_id': organization_id,
        'stats': {
            'total_projects': stats.accessible_projects if stats else 0,
            'total_members': total_members,
            'total_tasks': stats.total_tasks if stats else 0,
            'completed_tasks': stats.completed_tasks if stats else 0,
            'pending_tasks': (stats.total_tasks - stats.completed_tasks) if stats and stats.total_tasks and stats.completed_tasks else 0,
            'my_tasks': stats.my_tasks if stats else 0,
            'completion_rate': round((stats.completed_tasks / stats.total_tasks * 100) if stats and stats.total_tasks > 0 else 0, 2)
        },
        'recent_tasks': [
            {
                'id': str(t.id),
                'title': t.title,
                'status': t.status,
                'priority': t.priority,
                'updated_at': t.updated_at.isoformat()
            } for t in recent_tasks
        ],
        'permissions': {
            'can_create_projects': True,  # Based on org settings
            'can_invite_members': True,
            'can_manage_organization': False,
            'can_schedule_meetings': True,  # Based on org settings
            'can_view_all_data': True
        }
    }


@router.get("/member-dashboard")
async def get_member_dashboard(
    organization_id: Optional[str] = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get member dashboard data"""
    org_service = OrganizationService(db)
    
    # Get current organization if not specified
    if not organization_id:
        organization_id = await org_service.get_current_organization(str(current_user.id))
        if not organization_id:
            raise HTTPException(status_code=400, detail="No organization context")
    
    # Verify user is member
    result = await db.execute(
        select(OrganizationMember.role)
        .where(
            and_(
                OrganizationMember.user_id == current_user.id,
                OrganizationMember.organization_id == organization_id
            )
        )
    )
    
    role = result.scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=403, detail="Organization member access required")
    
    # Get member's assigned tasks
    tasks_result = await db.execute(
        select(
            func.count(Card.id.distinct()).label('total_tasks'),
            func.count(Card.id.distinct()).filter(Card.status == 'completed').label('completed_tasks'),
            func.count(Card.id.distinct()).filter(Card.status == 'in_progress').label('in_progress_tasks'),
            func.count(Card.id.distinct()).filter(Card.status == 'todo').label('todo_tasks')
        )
        .select_from(Card)
        .join(CardAssignment, CardAssignment.card_id == Card.id)
        .join(Board, Board.id == Card.board_id)
        .join(Project, Project.id == Board.project_id)
        .where(
            and_(
                CardAssignment.user_id == current_user.id,
                Project.organization_id == organization_id
            )
        )
    )
    
    stats = tasks_result.first()
    
    # Get recent assigned tasks
    recent_tasks_result = await db.execute(
        select(Card)
        .join(CardAssignment, CardAssignment.card_id == Card.id)
        .join(Board, Board.id == Card.board_id)
        .join(Project, Project.id == Board.project_id)
        .where(
            and_(
                CardAssignment.user_id == current_user.id,
                Project.organization_id == organization_id
            )
        )
        .order_by(Card.updated_at.desc())
        .limit(10)
    )
    recent_tasks = recent_tasks_result.scalars().all()
    
    # Get accessible projects (only those with assigned tasks)
    accessible_projects_result = await db.execute(
        select(Project)
        .join(Board, Board.project_id == Project.id)
        .join(Card, Card.board_id == Board.id)
        .join(CardAssignment, CardAssignment.card_id == Card.id)
        .where(
            and_(
                CardAssignment.user_id == current_user.id,
                Project.organization_id == organization_id
            )
        )
        .distinct()
    )
    accessible_projects = accessible_projects_result.scalars().all()
    
    return {
        'role': role,
        'organization_id': organization_id,
        'stats': {
            'total_tasks': stats.total_tasks if stats else 0,
            'completed_tasks': stats.completed_tasks if stats else 0,
            'in_progress_tasks': stats.in_progress_tasks if stats else 0,
            'todo_tasks': stats.todo_tasks if stats else 0,
            'completion_rate': round((stats.completed_tasks / stats.total_tasks * 100) if stats and stats.total_tasks > 0 else 0, 2)
        },
        'recent_tasks': [
            {
                'id': str(t.id),
                'title': t.title,
                'status': t.status,
                'priority': t.priority,
                'due_date': t.due_date.isoformat() if t.due_date else None,
                'updated_at': t.updated_at.isoformat()
            } for t in recent_tasks
        ],
        'accessible_projects': [
            {
                'id': str(p.id),
                'name': p.name,
                'status': p.status
            } for p in accessible_projects
        ],
        'permissions': {
            'can_create_projects': False,
            'can_invite_members': False,
            'can_manage_organization': False,
            'can_schedule_meetings': False,
            'can_view_all_data': False
        }
    }


@router.get("/dashboard-stats/{organization_id}")
async def get_dashboard_stats(
    organization_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get general dashboard statistics for any role"""
    # Verify user is member of organization
    result = await db.execute(
        select(OrganizationMember.role)
        .where(
            and_(
                OrganizationMember.user_id == current_user.id,
                OrganizationMember.organization_id == organization_id
            )
        )
    )
    
    role = result.scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=403, detail="Organization access required")
    
    # Get accessible projects based on role
    accessible_project_ids = await get_accessible_projects(organization_id, current_user, db)
    
    # Get statistics based on accessible projects
    if accessible_project_ids:
        stats_result = await db.execute(
            select(
                func.count(Project.id.distinct()).label('projects'),
                func.count(Card.id.distinct()).label('tasks'),
                func.count(Card.id.distinct()).filter(Card.status == 'completed').label('completed'),
                func.count(Card.id.distinct()).filter(CardAssignment.user_id == current_user.id).label('my_tasks')
            )
            .select_from(Project)
            .outerjoin(Board, Board.project_id == Project.id)
            .outerjoin(Card, Card.board_id == Board.id)
            .outerjoin(CardAssignment, CardAssignment.card_id == Card.id)
            .where(Project.id.in_(accessible_project_ids))
        )
        
        stats = stats_result.first()
    else:
        stats = None
    
    return {
        'role': role,
        'projects': stats.projects if stats else 0,
        'tasks': stats.tasks if stats else 0,
        'completed': stats.completed if stats else 0,
        'my_tasks': stats.my_tasks if stats else 0,
        'completion_rate': round((stats.completed / stats.tasks * 100) if stats and stats.tasks > 0 else 0, 2)
    }
