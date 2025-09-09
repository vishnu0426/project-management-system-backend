"""
AI Project Management endpoints for enhanced task management modal
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func
from sqlalchemy.orm import selectinload
from pydantic import BaseModel, Field
from uuid import UUID
import uuid
from datetime import datetime

from app.core.database import get_db
from app.core.deps import get_current_active_user, require_member
from app.core.exceptions import ValidationError, ResourceNotFoundError, InsufficientPermissionsError
from app.models.user import User
from app.models.organization import OrganizationMember
from app.models.project import Project
from app.models.board import Board
from app.models.column import Column
from app.models.card import Card, ChecklistItem
from app.models.ai_automation import SmartNotification
from app.services.ai_service import AIService
from app.services.role_permissions import role_permissions
from app.services.email_service import email_service

router = APIRouter()

# Pydantic models for AI project endpoints
class AIProjectPreviewRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    project_type: str = Field(default="general")
    team_size: int = Field(default=5, ge=2, le=20)
    team_experience: str = Field(default="intermediate")
    organization_id: str

class AIProjectPreviewResponse(BaseModel):
    project: Dict[str, Any]
    workflow: Dict[str, Any]
    tasks: List[Dict[str, Any]]
    suggestions: Optional[List[Dict[str, Any]]] = []
    metadata: Dict[str, Any]
    estimated_duration: int
    estimated_cost: float

class TaskReviewRequest(BaseModel):
    tasks: List[Dict[str, Any]]
    project_id: str
    modifications: Optional[Dict[str, Any]] = None

class TaskBulkUpdateRequest(BaseModel):
    task_ids: List[str]
    updates: Dict[str, Any]
    operation: str = Field(pattern="^(update|delete|assign|prioritize)$")

class ProjectWorkflowRequest(BaseModel):
    project_id: str
    workflow_data: Dict[str, Any]
    phase: str = Field(pattern="^(configure|overview|tech_stack|workflows|tasks)$")

class SmartSuggestionRequest(BaseModel):
    project_id: str
    context: Dict[str, Any]
    suggestion_type: str = Field(pattern="^(task_optimization|dependency|priority|assignment)$")

class ProjectConfirmationRequest(BaseModel):
    project_id: str
    confirmation_data: Dict[str, Any]
    final_tasks: List[Dict[str, Any]]
    workflow: Dict[str, Any]

class SimpleAIProjectRequest(BaseModel):
    name: str
    description: str
    organization_id: str
    generated_tasks: List[Dict[str, Any]]
    configuration: Optional[Dict[str, Any]] = {}
    tech_stack: Optional[Dict[str, Any]] = {}
    workflow: Optional[Dict[str, Any]] = {}

class AITaskToBoardRequest(BaseModel):
    project_id: str
    task_data: Dict[str, Any]
    organization_id: str

@router.post("/ai-preview", response_model=AIProjectPreviewResponse)
async def generate_ai_project_preview(
    request: AIProjectPreviewRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Generate AI project preview without creating the actual project"""
    # Check organization access
    org_member_result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == request.organization_id,
            OrganizationMember.user_id == current_user.id,
            OrganizationMember.role.in_(["owner"])  # Only owners can create AI projects
        )
    )
    org_member = org_member_result.scalar_one_or_none()
    if not org_member:
        raise InsufficientPermissionsError("Only organization owners can create AI projects")

    try:
        ai_service = AIService(db)
        preview_result = await ai_service.generate_ai_project_preview(
            project_name=request.name,
            organization_id=request.organization_id,
            user_id=str(current_user.id),
            project_type=request.project_type,
            team_size=request.team_size,
            team_experience=request.team_experience
        )

        return AIProjectPreviewResponse(**preview_result)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate AI project preview: {str(e)}")

@router.post("/ai-create-simple")
async def create_simple_ai_project(
    request: SimpleAIProjectRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create AI project with simple request format"""
    try:
        # Check organization access
        org_member_result = await db.execute(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == request.organization_id,
                OrganizationMember.user_id == current_user.id
            )
        )
        org_member = org_member_result.scalar_one_or_none()
        if not org_member:
            raise InsufficientPermissionsError("Access denied to organization")

        # Create the project
        project_id = str(uuid.uuid4())
        new_project = Project(
            id=project_id,
            name=request.name,
            description=request.description,
            organization_id=request.organization_id,
            created_by=current_user.id,
            status="active"
        )

        db.add(new_project)
        await db.commit()
        await db.refresh(new_project)

        # Send AI project creation confirmation email
        org_with_details = await db.execute(
            select(OrganizationMember)
            .options(selectinload(OrganizationMember.organization))
            .where(OrganizationMember.organization_id == request.organization_id)
            .where(OrganizationMember.user_id == current_user.id)
        )
        org_member_with_org = org_with_details.scalar_one_or_none()

        if org_member_with_org and org_member_with_org.organization:
            simple_ai_project_data = {
                "name": request.name,
                "description": request.description,
                "status": "active",
                "priority": "medium",
                "created_at": new_project.created_at.isoformat() if new_project.created_at else None,
                "project_id": project_id,
                "ai_generated": True,
                "tasks_count": len(request.generated_tasks) if hasattr(request, 'generated_tasks') and request.generated_tasks else 0
            }

            background_tasks.add_task(
                email_service.send_project_creation_confirmation,
                current_user.email,
                f"{current_user.first_name} {current_user.last_name}",
                simple_ai_project_data,
                org_member_with_org.organization.name
            )

        return {
            "success": True,
            "data": {
                "id": project_id,
                "name": request.name,
                "description": request.description,
                "organization_id": request.organization_id,
                "status": "active",
                "tasks_count": len(request.generated_tasks) if hasattr(request, 'generated_tasks') and request.generated_tasks else 0,
                "created_at": new_project.created_at.isoformat() if new_project.created_at else None
            },
            "message": "AI project created successfully"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create AI project: {str(e)}")

@router.post("/ai-create")
async def create_ai_project_from_preview(
    request: ProjectConfirmationRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create actual AI project from confirmed preview data"""
    try:
        ai_service = AIService(db)
        
        # Create project with confirmed data
        result = await ai_service.create_project_from_confirmation(
            confirmation_data=request.confirmation_data,
            final_tasks=request.final_tasks,
            workflow=request.workflow,
            user_id=str(current_user.id)
        )

        # Schedule background tasks for integrations
        background_tasks.add_task(
            ai_service.setup_project_integrations,
            result["project"]["id"],
            request.workflow
        )

        # Send AI project creation confirmation email
        if result.get("project"):
            project_data = result["project"]
            org_id = request.confirmation_data.get("organization_id")

            if org_id:
                # Get organization details
                org_result = await db.execute(
                    select(OrganizationMember)
                    .options(selectinload(OrganizationMember.organization))
                    .where(OrganizationMember.organization_id == org_id)
                    .where(OrganizationMember.user_id == current_user.id)
                )
                org_member = org_result.scalar_one_or_none()

                if org_member and org_member.organization:
                    ai_project_email_data = {
                        "name": project_data.get("name", "AI Generated Project"),
                        "description": project_data.get("description", ""),
                        "status": "active",
                        "priority": "medium",
                        "created_at": datetime.utcnow().isoformat(),
                        "project_id": project_data.get("id"),
                        "ai_generated": True,
                        "tasks_count": len(request.final_tasks) if request.final_tasks else 0,
                        "workflow_phases": request.workflow.get("phases", []) if request.workflow else [],
                        "tech_stack": request.confirmation_data.get("tech_stack", {}),
                        "team_size": request.confirmation_data.get("team_size"),
                        "estimated_duration": request.confirmation_data.get("estimated_duration")
                    }

                    background_tasks.add_task(
                        email_service.send_project_creation_confirmation,
                        current_user.email,
                        f"{current_user.first_name} {current_user.last_name}",
                        ai_project_email_data,
                        org_member.organization.name
                    )

        return {
            "success": True,
            "data": result,
            "message": "AI project created successfully"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create AI project: {str(e)}")

@router.put("/tasks/bulk-update")
async def bulk_update_tasks(
    request: TaskBulkUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Bulk update multiple tasks"""
    try:
        # Validate access to all tasks
        cards_result = await db.execute(
            select(Card)
            .options(
                selectinload(Card.column)
                .selectinload(Column.board)
                .selectinload(Board.project)
            )
            .where(Card.id.in_(request.task_ids))
        )
        cards = cards_result.scalars().all()

        if len(cards) != len(request.task_ids):
            raise ResourceNotFoundError("Some tasks not found")

        # Check permissions for each task
        for card in cards:
            org_member_result = await db.execute(
                select(OrganizationMember).where(
                    OrganizationMember.organization_id == card.column.board.project.organization_id,
                    OrganizationMember.user_id == current_user.id
                )
            )
            org_member = org_member_result.scalar_one_or_none()
            if not org_member:
                raise InsufficientPermissionsError("Access denied to one or more tasks")

        # Perform bulk operation
        if request.operation == "update":
            await db.execute(
                update(Card)
                .where(Card.id.in_(request.task_ids))
                .values(**request.updates)
            )
        elif request.operation == "delete":
            await db.execute(
                delete(Card)
                .where(Card.id.in_(request.task_ids))
            )

        await db.commit()

        return {
            "success": True,
            "data": {
                "updated_count": len(request.task_ids),
                "operation": request.operation
            },
            "message": f"Successfully {request.operation}d {len(request.task_ids)} tasks"
        }

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Bulk update failed: {str(e)}")

@router.post("/workflow/update")
async def update_project_workflow(
    request: ProjectWorkflowRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Update project workflow for specific phase"""
    try:
        # Get project and check access
        project_result = await db.execute(
            select(Project).where(Project.id == request.project_id)
        )
        project = project_result.scalar_one_or_none()
        if not project:
            raise ResourceNotFoundError("Project not found")

        # Check permissions
        org_member_result = await db.execute(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == project.organization_id,
                OrganizationMember.user_id == current_user.id,
                OrganizationMember.role.in_(["owner", "admin"])
            )
        )
        org_member = org_member_result.scalar_one_or_none()
        if not org_member:
            raise InsufficientPermissionsError("Insufficient permissions to update workflow")

        ai_service = AIService(db)
        updated_workflow = await ai_service.update_project_workflow(
            project_id=request.project_id,
            phase=request.phase,
            workflow_data=request.workflow_data
        )

        return {
            "success": True,
            "data": updated_workflow,
            "message": f"Workflow updated for {request.phase} phase"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update workflow: {str(e)}")

@router.post("/suggestions/generate")
async def generate_smart_suggestions(
    request: SmartSuggestionRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Generate smart suggestions for project optimization"""
    try:
        # Get project and check access
        project_result = await db.execute(
            select(Project).where(Project.id == request.project_id)
        )
        project = project_result.scalar_one_or_none()
        if not project:
            raise ResourceNotFoundError("Project not found")

        # Check permissions
        org_member_result = await db.execute(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == project.organization_id,
                OrganizationMember.user_id == current_user.id
            )
        )
        org_member = org_member_result.scalar_one_or_none()
        if not org_member:
            raise InsufficientPermissionsError("Access denied to project")

        ai_service = AIService(db)
        suggestions = await ai_service.generate_smart_suggestions(
            project_id=request.project_id,
            suggestion_type=request.suggestion_type,
            context=request.context
        )

        return {
            "success": True,
            "data": suggestions,
            "message": "Smart suggestions generated successfully"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate suggestions: {str(e)}")

@router.post("/ai-task-to-board")
async def convert_ai_task_to_board_card(
    request: AITaskToBoardRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Convert an AI-generated task to a board card and notify project admins"""
    try:
        # Check organization access
        org_member_result = await db.execute(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == request.organization_id,
                OrganizationMember.user_id == current_user.id,
                OrganizationMember.role.in_(["owner", "admin"])  # Only owners/admins can create tasks
            )
        )
        org_member = org_member_result.scalar_one_or_none()
        if not org_member:
            raise InsufficientPermissionsError("Only organization owners/admins can create tasks from AI suggestions")

        # Get the project and verify access
        project_result = await db.execute(
            select(Project).where(
                Project.id == request.project_id,
                Project.organization_id == request.organization_id
            )
        )
        project = project_result.scalar_one_or_none()
        if not project:
            raise ResourceNotFoundError("Project not found")

        # Find the project's board
        board_result = await db.execute(
            select(Board).where(Board.project_id == request.project_id)
        )
        board = board_result.scalar_one_or_none()
        if not board:
            raise ResourceNotFoundError("Project board not found")

        # Find the "To Do" column (or first column if "To Do" doesn't exist)
        todo_column_result = await db.execute(
            select(Column).where(
                Column.board_id == board.id,
                Column.name.ilike('%to%do%')
            ).order_by(Column.position)
        )
        todo_column = todo_column_result.scalar_one_or_none()

        if not todo_column:
            # If no "To Do" column, get the first column
            first_column_result = await db.execute(
                select(Column).where(Column.board_id == board.id)
                .order_by(Column.position)
            )
            todo_column = first_column_result.scalar_one_or_none()

        if not todo_column:
            raise ResourceNotFoundError("No columns found in project board")

        # Get the next position for the card
        max_position_result = await db.execute(
            select(func.max(Card.position)).where(Card.column_id == todo_column.id)
        )
        max_position = max_position_result.scalar() or 0
        next_position = max_position + 1

        # Extract task data
        task_data = request.task_data

        # Create the card
        card = Card(
            column_id=todo_column.id,
            title=task_data.get('title', 'AI Generated Task'),
            description=task_data.get('description', ''),
            position=next_position,
            priority=task_data.get('priority', 'medium'),
            created_by=current_user.id
        )

        db.add(card)
        await db.flush()  # Get the card ID

        # Add checklist items if provided
        checklist_items = task_data.get('checklist', [])
        if checklist_items:
            for idx, item_text in enumerate(checklist_items):
                if isinstance(item_text, str):
                    checklist_item = ChecklistItem(
                        card_id=card.id,
                        text=item_text,
                        position=idx,
                        ai_generated=True,
                        confidence=0.85,
                        created_by=current_user.id
                    )
                    db.add(checklist_item)

        await db.commit()
        await db.refresh(card)

        # Schedule notification to project admins
        background_tasks.add_task(
            notify_project_admins_about_new_task,
            db,
            request.organization_id,
            request.project_id,
            card.id,
            task_data.get('title', 'AI Generated Task'),
            current_user.id
        )

        return {
            "success": True,
            "data": {
                "card_id": str(card.id),
                "title": card.title,
                "column_name": todo_column.name,
                "board_id": str(board.id),
                "project_id": str(project.id),
                "position": card.position,
                "checklist_items_count": len(checklist_items)
            },
            "message": "AI task successfully converted to board card"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to convert AI task to board card: {str(e)}")


async def notify_project_admins_about_new_task(
    db: AsyncSession,
    organization_id: str,
    project_id: str,
    card_id: str,
    task_title: str,
    creator_id: str
):
    """Send notifications to project admins about new AI-generated task"""
    try:
        # Find all admins and owners in the organization
        admin_members_result = await db.execute(
            select(OrganizationMember, User).join(
                User, OrganizationMember.user_id == User.id
            ).where(
                OrganizationMember.organization_id == organization_id,
                OrganizationMember.role.in_(["admin", "owner"]),
                OrganizationMember.user_id != creator_id  # Don't notify the creator
            )
        )
        admin_members = admin_members_result.all()

        # Get project name for the notification
        project_result = await db.execute(
            select(Project).where(Project.id == project_id)
        )
        project = project_result.scalar_one_or_none()
        project_name = project.name if project else "Unknown Project"

        # Get creator name
        creator_result = await db.execute(
            select(User).where(User.id == creator_id)
        )
        creator = creator_result.scalar_one_or_none()
        creator_name = f"{creator.first_name} {creator.last_name}" if creator else "Unknown User"

        # Create notifications for each admin
        for member, user in admin_members:
            notification = SmartNotification(
                organization_id=organization_id,
                user_id=user.id,
                notification_type='ai_task_created',
                title='New AI Task Added to Project',
                message=f'{creator_name} added a new AI-generated task "{task_title}" to project "{project_name}". The task has been placed in the To Do column and is ready for assignment.',
                priority='medium',
                context_data={
                    'project_id': project_id,
                    'project_name': project_name,
                    'card_id': card_id,
                    'task_title': task_title,
                    'creator_id': creator_id,
                    'creator_name': creator_name,
                    'action_url': f'/projects/{project_id}/board',
                    'ai_generated': True
                },
                ai_generated=True,
                delivery_method='in_app'
            )

            db.add(notification)

        await db.commit()

        print(f"✅ Sent notifications to {len(admin_members)} project admins about new AI task: {task_title}")

    except Exception as e:
        print(f"❌ Failed to send notifications about new AI task: {str(e)}")
        # Don't raise the exception as this is a background task

@router.post("/suggestions/apply")
async def apply_smart_suggestion(
    suggestion_id: str,
    project_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Apply a smart suggestion to the project"""
    try:
        ai_service = AIService(db)
        result = await ai_service.apply_smart_suggestion(
            suggestion_id=suggestion_id,
            project_id=project_id,
            user_id=str(current_user.id)
        )

        return {
            "success": True,
            "data": result,
            "message": "Suggestion applied successfully"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to apply suggestion: {str(e)}")

@router.get("/templates")
async def get_project_templates(
    project_type: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get available project templates"""
    try:
        ai_service = AIService(db)
        templates = await ai_service.get_project_templates(project_type=project_type)

        return {
            "success": True,
            "data": templates,
            "message": "Project templates retrieved successfully"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get templates: {str(e)}")

@router.get("/tech-stacks")
async def get_tech_stacks(
    project_type: Optional[str] = None,
    current_user: User = Depends(get_current_active_user)
):
    """Get available technology stacks for projects"""
    try:
        # This would typically come from a database or external service
        tech_stacks = {
            "web_application": [
                {"name": "React + Node.js", "technologies": ["React", "Node.js", "Express", "PostgreSQL"]},
                {"name": "Vue + Python", "technologies": ["Vue.js", "Python", "Django", "PostgreSQL"]},
                {"name": "Angular + .NET", "technologies": ["Angular", ".NET Core", "SQL Server"]}
            ],
            "mobile_app": [
                {"name": "React Native", "technologies": ["React Native", "Node.js", "MongoDB"]},
                {"name": "Flutter", "technologies": ["Flutter", "Dart", "Firebase"]},
                {"name": "Native iOS/Android", "technologies": ["Swift", "Kotlin", "REST APIs"]}
            ],
            "general": [
                {"name": "Modern Web Stack", "technologies": ["JavaScript", "HTML5", "CSS3", "Database"]},
                {"name": "Cloud Native", "technologies": ["Docker", "Kubernetes", "Microservices"]},
                {"name": "Data Analytics", "technologies": ["Python", "Pandas", "Jupyter", "SQL"]}
            ]
        }

        filtered_stacks = tech_stacks.get(project_type, tech_stacks["general"]) if project_type else tech_stacks

        return {
            "success": True,
            "data": filtered_stacks,
            "message": "Technology stacks retrieved successfully"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get tech stacks: {str(e)}")
