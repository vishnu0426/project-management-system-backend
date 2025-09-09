"""
Task Assignment and Notification System
Handle task assignment with member notifications and acceptance workflow
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.deps import get_current_active_user
from app.models.user import User
from app.models.organization import OrganizationMember
from app.models.project import Project
from app.models.board import Board
from app.models.column import Column
from app.models.card import Card, CardAssignment
from app.models.ai_automation import SmartNotification
from app.services.organization_service import OrganizationService
from app.middleware.role_based_access import require_permission, get_accessible_projects
from app.services.enhanced_role_permissions import Permission

router = APIRouter()


@router.post("/assign-task")
@require_permission(Permission.ASSIGN_TASK)
async def assign_task_to_members(
    task_data: dict,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Assign task to team members with notifications"""
    
    # Extract task data
    title = task_data.get('title')
    description = task_data.get('description', '')
    assigned_to = task_data.get('assigned_to', [])  # List of user IDs
    priority = task_data.get('priority', 'medium')
    due_date_str = task_data.get('due_date')

    # Parse due_date if provided
    due_date = None
    if due_date_str:
        try:
            # Handle ISO format datetime strings
            if isinstance(due_date_str, str):
                due_date = datetime.fromisoformat(due_date_str.replace('Z', '+00:00'))
            else:
                due_date = due_date_str
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid due_date format. Use ISO format (YYYY-MM-DDTHH:MM:SSZ)")

    project_id = task_data.get('project_id')
    board_id = task_data.get('board_id')
    column_id = task_data.get('column_id')
    organization_id = task_data.get('organization_id')
    
    if not title or not assigned_to:
        raise HTTPException(status_code=400, detail="Title and assigned_to are required")
    
    # Get organization context if not provided
    if not organization_id:
        org_service = OrganizationService(db)
        organization_id = await org_service.get_current_organization(str(current_user.id))
        if not organization_id:
            raise HTTPException(status_code=400, detail="No organization context")
    
    # Verify all assigned users are members of the organization
    for user_id in assigned_to:
        member_result = await db.execute(
            select(OrganizationMember)
            .where(
                and_(
                    OrganizationMember.user_id == user_id,
                    OrganizationMember.organization_id == organization_id
                )
            )
        )
        
        if not member_result.scalar_one_or_none():
            raise HTTPException(
                status_code=400, 
                detail=f"User {user_id} is not a member of this organization"
            )
    
    # Get or create project/board/column if needed
    if not project_id:
        # Create default project if none specified
        project = Project(
            organization_id=organization_id,
            name=f"Tasks - {title}",
            description="Auto-created project for task assignment",
            created_by=current_user.id
        )
        db.add(project)
        await db.flush()
        project_id = project.id
    
    if not board_id:
        # Create default board
        board = Board(
            project_id=project_id,
            name="Task Board",
            description="Auto-created board for task assignment",
            created_by=current_user.id
        )
        db.add(board)
        await db.flush()
        board_id = board.id
    
    if not column_id:
        # Create default column
        column = Column(
            board_id=board_id,
            name="To Do",
            position=0
        )
        db.add(column)
        await db.flush()
        column_id = column.id
    
    # Create the task card
    card = Card(
        column_id=column_id,
        title=title,
        description=description,
        priority=priority,
        due_date=due_date,
        status='todo',
        position=0,  # Add position field which is required
        created_by=current_user.id
    )
    
    db.add(card)
    await db.flush()
    
    # Create card assignments
    assignments = []
    for user_id in assigned_to:
        assignment = CardAssignment(
            card_id=card.id,
            user_id=user_id,
            assigned_by=current_user.id
        )
        assignments.append(assignment)
        db.add(assignment)
    
    await db.commit()
    
    # Send notifications to assigned members
    background_tasks.add_task(
        send_task_assignment_notifications,
        card.id,
        assigned_to,
        current_user.id,
        organization_id,
        db
    )
    
    return {
        'success': True,
        'task_id': str(card.id),
        'message': f'Task "{title}" assigned to {len(assigned_to)} members',
        'assigned_to': [str(uid) for uid in assigned_to],
        'notifications_sent': len(assigned_to)
    }


@router.post("/accept-task/{task_id}")
async def accept_task_assignment(
    task_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Accept task assignment (members only)"""
    
    # Get card assignment
    assignment_result = await db.execute(
        select(CardAssignment)
        .where(
            and_(
                CardAssignment.card_id == task_id,
                CardAssignment.user_id == current_user.id,
                CardAssignment.status == 'pending'
            )
        )
    )
    
    assignment = assignment_result.scalar_one_or_none()
    if not assignment:
        raise HTTPException(
            status_code=404, 
            detail="Task assignment not found or already processed"
        )
    
    # Update assignment status
    assignment.status = 'accepted'
    assignment.accepted_at = func.now()
    
    # Get card details for notification
    card_result = await db.execute(
        select(Card).where(Card.id == task_id)
    )
    card = card_result.scalar_one_or_none()
    
    if not card:
        raise HTTPException(status_code=404, detail="Task not found")
    
    await db.commit()
    
    # Notify admin/owner about acceptance
    await send_task_acceptance_notification(
        card, current_user.id, assignment.assigned_by, db
    )
    
    return {
        'success': True,
        'message': f'Task "{card.title}" accepted successfully',
        'task_id': str(task_id),
        'status': 'accepted'
    }


@router.get("/my-assigned-tasks")
async def get_my_assigned_tasks(
    status: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get tasks assigned to current user"""
    
    # Build query
    query = select(Card, CardAssignment).join(
        CardAssignment, CardAssignment.card_id == Card.id
    ).where(CardAssignment.user_id == current_user.id)
    
    # Apply status filter
    if status:
        query = query.where(CardAssignment.status == status)
    
    # Order by priority and due date
    query = query.order_by(
        Card.priority.desc(),
        Card.due_date.asc().nullslast(),
        Card.created_at.desc()
    )
    
    result = await db.execute(query)
    tasks_and_assignments = result.all()
    
    tasks = []
    for card, assignment in tasks_and_assignments:
        # Get project and board info
        project_result = await db.execute(
            select(Project).where(Project.id == card.project_id)
        )
        project = project_result.scalar_one_or_none()
        
        board_result = await db.execute(
            select(Board).where(Board.id == card.board_id)
        )
        board = board_result.scalar_one_or_none()
        
        tasks.append({
            'id': str(card.id),
            'title': card.title,
            'description': card.description,
            'priority': card.priority,
            'status': card.status,
            'due_date': card.due_date.isoformat() if card.due_date else None,
            'assignment_status': assignment.status,
            'assigned_at': assignment.assigned_at.isoformat(),
            'accepted_at': assignment.accepted_at.isoformat() if assignment.accepted_at else None,
            'project': {
                'id': str(project.id),
                'name': project.name
            } if project else None,
            'board': {
                'id': str(board.id),
                'name': board.name
            } if board else None
        })
    
    return {
        'tasks': tasks,
        'total_count': len(tasks),
        'pending_count': len([t for t in tasks if t['assignment_status'] == 'pending']),
        'accepted_count': len([t for t in tasks if t['assignment_status'] == 'accepted'])
    }


@router.get("/team-assignments/{organization_id}")
@require_permission(Permission.VIEW_ALL_TASKS)
async def get_team_assignments(
    organization_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all task assignments for team (admin/owner only)"""
    
    # Get all assignments in organization
    result = await db.execute(
        select(Card, CardAssignment, User)
        .join(CardAssignment, CardAssignment.card_id == Card.id)
        .join(User, User.id == CardAssignment.user_id)
        .join(Project, Project.id == Card.project_id)
        .where(Project.organization_id == organization_id)
        .order_by(Card.created_at.desc())
    )
    
    assignments_data = result.all()
    
    assignments = []
    for card, assignment, user in assignments_data:
        assignments.append({
            'task_id': str(card.id),
            'task_title': card.title,
            'task_priority': card.priority,
            'task_status': card.status,
            'assigned_to': {
                'id': str(user.id),
                'name': f"{user.first_name} {user.last_name}",
                'email': user.email
            },
            'assignment_status': assignment.status,
            'assigned_at': assignment.assigned_at.isoformat(),
            'accepted_at': assignment.accepted_at.isoformat() if assignment.accepted_at else None
        })
    
    # Get summary statistics
    total_assignments = len(assignments)
    pending_assignments = len([a for a in assignments if a['assignment_status'] == 'pending'])
    accepted_assignments = len([a for a in assignments if a['assignment_status'] == 'accepted'])
    
    return {
        'assignments': assignments,
        'summary': {
            'total_assignments': total_assignments,
            'pending_assignments': pending_assignments,
            'accepted_assignments': accepted_assignments,
            'acceptance_rate': round((accepted_assignments / total_assignments * 100) if total_assignments > 0 else 0, 2)
        }
    }


async def send_task_assignment_notifications(
    task_id: str,
    assigned_user_ids: List[str],
    assigner_id: str,
    organization_id: str,
    db: AsyncSession
):
    """Background task to send assignment notifications"""
    try:
        # Get task details
        card_result = await db.execute(
            select(Card).where(Card.id == task_id)
        )
        card = card_result.scalar_one_or_none()
        
        if not card:
            return
        
        # Get assigner details
        assigner_result = await db.execute(
            select(User).where(User.id == assigner_id)
        )
        assigner = assigner_result.scalar_one_or_none()
        
        # Send notification to each assigned user
        for user_id in assigned_user_ids:
            notification = SmartNotification(
                organization_id=organization_id,
                user_id=user_id,
                notification_type='task_assignment',
                title=f'New Task Assigned: {card.title}',
                message=f'{assigner.first_name} {assigner.last_name} assigned you a new task: "{card.title}"',
                priority='normal',
                context_data={
                    'task_id': str(task_id),
                    'task_title': card.title,
                    'assigner_id': str(assigner_id),
                    'assigner_name': f'{assigner.first_name} {assigner.last_name}',
                    'action_required': 'accept_task'
                },
                ai_generated=False,
                delivery_method='in_app'
            )
            
            db.add(notification)
        
        await db.commit()
        print(f"✅ Sent task assignment notifications for task {task_id} to {len(assigned_user_ids)} users")
        
    except Exception as e:
        print(f"❌ Failed to send task assignment notifications: {str(e)}")


async def send_task_acceptance_notification(
    card: Card,
    accepter_id: str,
    assigner_id: str,
    db: AsyncSession
):
    """Send notification when task is accepted"""
    try:
        # Get accepter details
        accepter_result = await db.execute(
            select(User).where(User.id == accepter_id)
        )
        accepter = accepter_result.scalar_one_or_none()
        
        # Get project for organization context
        project_result = await db.execute(
            select(Project).where(Project.id == card.project_id)
        )
        project = project_result.scalar_one_or_none()
        
        if not accepter or not project:
            return
        
        # Send notification to assigner
        notification = SmartNotification(
            organization_id=project.organization_id,
            user_id=assigner_id,
            notification_type='task_accepted',
            title=f'Task Accepted: {card.title}',
            message=f'{accepter.first_name} {accepter.last_name} accepted the task: "{card.title}"',
            priority='low',
            context_data={
                'task_id': str(card.id),
                'task_title': card.title,
                'accepter_id': str(accepter_id),
                'accepter_name': f'{accepter.first_name} {accepter.last_name}'
            },
            ai_generated=False,
            delivery_method='in_app'
        )
        
        db.add(notification)
        await db.commit()
        
        print(f"✅ Sent task acceptance notification for task {card.id}")
        
    except Exception as e:
        print(f"❌ Failed to send task acceptance notification: {str(e)}")
