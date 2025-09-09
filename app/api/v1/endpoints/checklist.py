"""
Checklist management endpoints
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.deps import get_current_active_user
from app.core.exceptions import ResourceNotFoundError, InsufficientPermissionsError, ValidationError
from app.models.user import User
from app.models.organization import OrganizationMember
from app.models.card import Card, ChecklistItem
from app.models.column import Column
from app.models.board import Board
from app.services.role_permissions import role_permissions
from app.schemas.checklist import (
    ChecklistItemCreate, ChecklistItemUpdate, ChecklistItemResponse,
    ChecklistBulkCreate, AIChecklistRequest, AIChecklistResponse,
    ChecklistSuggestionsResponse, ChecklistProgressResponse,
    ChecklistValidationRequest, ChecklistValidationResponse,
    RolePermissionsResponse, AssignableMembersResponse
)
from app.services.role_permissions import role_permissions
from app.services.ai_checklist_service import ai_checklist_service

router = APIRouter()


@router.post("/cards/{card_id}/checklist/ai-generate", response_model=AIChecklistResponse)
async def generate_ai_checklist(
    card_id: str,
    request: AIChecklistRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Generate AI-powered checklist for a card"""
    # Check card access
    result = await db.execute(
        select(Card)
        .options(
            selectinload(Card.column)
            .selectinload(Column.board)
            .selectinload(Board.project)
        )
        .where(Card.id == card_id)
    )
    card = result.scalar_one_or_none()
    if not card:
        raise ResourceNotFoundError("Card not found")
    
    # Check organization membership
    org_member_result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == card.column.board.project.organization_id,
            OrganizationMember.user_id == current_user.id
        )
    )
    org_member = org_member_result.scalar_one_or_none()
    if not org_member:
        raise InsufficientPermissionsError("Access denied")
    
    # Check if user can create tasks
    if not role_permissions.can_create_tasks(org_member.role):
        raise InsufficientPermissionsError("Insufficient permissions to generate checklist")
    
    # Generate AI checklist
    ai_result = await ai_checklist_service.generate_ai_checklist(
        title=request.title,
        description=request.description,
        priority=request.priority,
        project_type=request.project_type
    )
    
    return AIChecklistResponse(**ai_result)

@router.post("/{card_id}/generate-ai", response_model=AIChecklistResponse)
async def generate_ai_checklist_alias(
    card_id: str,
    request: AIChecklistRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Alias endpoint: Generate AI-powered checklist via `/checklist/{card_id}/generate-ai`.

    Delegates to the existing `generate_ai_checklist` handler defined on the
    nested `/cards/{card_id}/checklist/ai-generate` route.  This alias exists
    because the front-end client calls `/api/v1/checklist/{cardId}/generate-ai`.
    """
    return await generate_ai_checklist(card_id=card_id, request=request, current_user=current_user, db=db)


@router.post("/cards/{card_id}/checklist", response_model=List[ChecklistItemResponse])
async def create_checklist_items(
    card_id: str,
    request: ChecklistBulkCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create multiple checklist items for a card"""
    # Check card access
    result = await db.execute(
        select(Card)
        .options(
            selectinload(Card.column)
            .selectinload(Column.board)
            .selectinload(Board.project)
        )
        .where(Card.id == card_id)
    )
    card = result.scalar_one_or_none()
    if not card:
        raise ResourceNotFoundError("Card not found")
    
    # Check organization membership and permissions
    org_member_result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == card.column.board.project.organization_id,
            OrganizationMember.user_id == current_user.id
        )
    )
    org_member = org_member_result.scalar_one_or_none()
    if not org_member:
        raise InsufficientPermissionsError("Access denied")
    
    # Check if user can edit the task
    is_task_creator = str(card.created_by) == str(current_user.id)
    if not role_permissions.can_edit_task(org_member.role, is_task_creator):
        raise InsufficientPermissionsError("Insufficient permissions to modify checklist")
    
    # Create checklist items
    created_items = []
    for item_data in request.items:
        checklist_item = ChecklistItem(
            card_id=card_id,
            text=item_data.text,
            position=item_data.position,
            ai_generated=item_data.ai_generated,
            confidence=item_data.confidence,
            ai_metadata=item_data.metadata,
            created_by=current_user.id
        )
        db.add(checklist_item)
        created_items.append(checklist_item)
    
    await db.commit()
    
    # Refresh items to get IDs
    for item in created_items:
        await db.refresh(item)
    
    return [ChecklistItemResponse.from_orm(item) for item in created_items]

# -----------------------------------------------------------------------------
# Alias endpoints for checklist operations
#
# The front‑end calls `POST /api/v1/checklist/{cardId}/bulk` to create multiple
# checklist items for a card.  The original implementation exposes
# `/api/v1/checklist/cards/{card_id}/checklist`, which does not match the
# client‑expected path.  To provide a compatible endpoint without duplicating
# business logic, we define an alias here that forwards to the existing
# `create_checklist_items` handler.

@router.post("/{card_id}/bulk", response_model=List[ChecklistItemResponse])
async def create_checklist_items_bulk_alias(
    card_id: str,
    request: ChecklistBulkCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Alias endpoint: Bulk create checklist items via `/checklist/{card_id}/bulk`.

    This wrapper delegates to the main `create_checklist_items` handler while
    allowing the client to call `/api/v1/checklist/{cardId}/bulk` as expected.
    """
    return await create_checklist_items(card_id=card_id, request=request, current_user=current_user, db=db)


@router.get("/cards/{card_id}/checklist", response_model=List[ChecklistItemResponse])
async def get_checklist_items(
    card_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all checklist items for a card"""
    # Check card access
    result = await db.execute(
        select(Card)
        .options(
            selectinload(Card.column)
            .selectinload(Column.board)
            .selectinload(Board.project)
        )
        .where(Card.id == card_id)
    )
    card = result.scalar_one_or_none()
    if not card:
        raise ResourceNotFoundError("Card not found")
    
    # Check organization membership
    org_member_result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == card.column.board.project.organization_id,
            OrganizationMember.user_id == current_user.id
        )
    )
    if not org_member_result.scalar_one_or_none():
        raise InsufficientPermissionsError("Access denied")
    
    # Get checklist items
    items_result = await db.execute(
        select(ChecklistItem)
        .where(ChecklistItem.card_id == card_id)
        .order_by(ChecklistItem.position)
    )
    items = items_result.scalars().all()
    
    return [ChecklistItemResponse.from_orm(item) for item in items]


@router.put("/checklist/{item_id}", response_model=ChecklistItemResponse)
async def update_checklist_item(
    item_id: str,
    item_data: ChecklistItemUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a checklist item"""
    # Get checklist item with card info
    result = await db.execute(
        select(ChecklistItem)
        .options(
            selectinload(ChecklistItem.card)
            .selectinload(Card.column)
            .selectinload(Column.board)
            .selectinload(Board.project)
        )
        .where(ChecklistItem.id == item_id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise ResourceNotFoundError("Checklist item not found")
    
    # Check organization membership and permissions
    org_member_result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == item.card.column.board.project.organization_id,
            OrganizationMember.user_id == current_user.id
        )
    )
    org_member = org_member_result.scalar_one_or_none()
    if not org_member:
        raise InsufficientPermissionsError("Access denied")
    
    # Check if user can edit the task
    is_task_creator = str(item.card.created_by) == str(current_user.id)
    if not role_permissions.can_edit_task(org_member.role, is_task_creator):
        raise InsufficientPermissionsError("Insufficient permissions to modify checklist")
    
    # Update fields
    if item_data.text is not None:
        item.text = item_data.text

    # Handle both 'completed' and 'is_completed' field names
    is_completed = item_data.is_completed if item_data.is_completed is not None else item_data.completed
    if is_completed is not None:
        from datetime import datetime, timezone
        item.completed = is_completed
        item.completed_at = datetime.now(timezone.utc) if is_completed else None

    if item_data.position is not None:
        item.position = item_data.position
    
    await db.commit()
    await db.refresh(item)

    # After updating the item, check if the card is now fully complete.
    # If all checklist items on the card are completed, mark the card as
    # completed (status='completed') and send appropriate notifications.
    try:
        from sqlalchemy import func
        from app.models.project import Project
        from app.services.enhanced_notification_service import EnhancedNotificationService

        # Count incomplete items for the card
        incomplete_count_result = await db.execute(
            select(func.count(ChecklistItem.id)).where(
                ChecklistItem.card_id == item.card_id,
                ChecklistItem.completed == False  # noqa: E712 – explicit comparison is intentional
            )
        )
        incomplete_count = incomplete_count_result.scalar_one_or_none() or 0

        # If no incomplete items remain, mark the card as completed
        if incomplete_count == 0:
            # Reload the card with related data
            card_result = await db.execute(
                select(Card)
                .options(
                    selectinload(Card.column)
                    .selectinload(Column.board)
                    .selectinload(Board.project)
                )
                .where(Card.id == item.card_id)
            )
            card_obj = card_result.scalar_one_or_none()
            if card_obj:
                # Update card status if not already completed
                if card_obj.status != 'completed':
                    card_obj.status = 'completed'
                    await db.commit()
                    await db.refresh(card_obj)

                # Send notifications about task completion
                notification_service = EnhancedNotificationService(db)
                org_id = str(card_obj.column.board.project.organization_id)
                await notification_service.send_task_completion_notification(
                    card_id=str(card_obj.id),
                    completed_by=str(current_user.id),
                    organization_id=org_id
                )

                # Send a project completion reminder if applicable
                await notification_service.send_project_completion_reminder(
                    project_id=str(card_obj.column.board.project.id)
                )
    except Exception:
        # Suppress exceptions in notification logic to avoid affecting the main response
        pass

    return ChecklistItemResponse.from_orm(item)

# -----------------------------------------------------------------------------
# Alias endpoints for checklist item manipulation
#
# The front‑end expects to update and delete checklist items via
# `/api/v1/checklist/items/{itemId}` rather than the original
# `/api/v1/checklist/checklist/{itemId}`.  To provide compatibility, we
# implement thin wrappers that delegate to the existing handlers.

@router.put("/items/{item_id}", response_model=ChecklistItemResponse)
async def update_checklist_item_alias(
    item_id: str,
    item_data: ChecklistItemUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Alias endpoint: Update a checklist item via `/checklist/items/{item_id}`.

    Delegates to the `update_checklist_item` handler, preserving all
    authorization and business logic.
    """
    return await update_checklist_item(item_id=item_id, item_data=item_data, current_user=current_user, db=db)


@router.delete("/checklist/{item_id}")
async def delete_checklist_item(
    item_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a checklist item"""
    # Get checklist item with card info
    result = await db.execute(
        select(ChecklistItem)
        .options(
            selectinload(ChecklistItem.card)
            .selectinload(Card.column)
            .selectinload(Column.board)
            .selectinload(Board.project)
        )
        .where(ChecklistItem.id == item_id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise ResourceNotFoundError("Checklist item not found")
    
    # Check organization membership and permissions
    org_member_result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == item.card.column.board.project.organization_id,
            OrganizationMember.user_id == current_user.id
        )
    )
    org_member = org_member_result.scalar_one_or_none()
    if not org_member:
        raise InsufficientPermissionsError("Access denied")
    
    # Check if user can edit the task
    is_task_creator = str(item.card.created_by) == str(current_user.id)
    if not role_permissions.can_edit_task(org_member.role, is_task_creator):
        raise InsufficientPermissionsError("Insufficient permissions to modify checklist")

    # Check if project data is protected
    project = item.card.column.board.project
    if project.data_protected:
        # Only owners can delete checklist items from protected projects
        if org_member.role != 'owner':
            raise HTTPException(
                status_code=403,
                detail=f"Cannot delete checklist item: Project data is protected. Reason: {project.protection_reason or 'Data protection enabled'}"
            )

        # Even owners get a warning about protected data
        if project.sign_off_requested and not project.sign_off_approved:
            raise HTTPException(
                status_code=403,
                detail="Cannot delete checklist item: Project is pending sign-off approval. Complete the sign-off process first."
            )

    await db.delete(item)
    await db.commit()

    return {"success": True, "message": "Checklist item deleted successfully"}

@router.delete("/items/{item_id}")
async def delete_checklist_item_alias(
    item_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Alias endpoint: Delete a checklist item via `/checklist/items/{item_id}`.

    Delegates to the `delete_checklist_item` handler.
    """
    return await delete_checklist_item(item_id=item_id, current_user=current_user, db=db)


@router.get("/checklist/suggestions/{task_type}", response_model=ChecklistSuggestionsResponse)
async def get_checklist_suggestions(
    task_type: str,
    current_user: User = Depends(get_current_active_user)
):
    """Get suggested checklist items for a task type"""
    suggestions = ai_checklist_service.get_suggested_items(task_type)
    
    return ChecklistSuggestionsResponse(
        suggestions=suggestions,
        task_type=task_type
    )


@router.get("/cards/{card_id}/checklist/progress", response_model=ChecklistProgressResponse)
async def get_checklist_progress(
    card_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get checklist progress for a card"""
    # Check card access
    result = await db.execute(
        select(Card)
        .options(
            selectinload(Card.column)
            .selectinload(Column.board)
            .selectinload(Board.project)
        )
        .where(Card.id == card_id)
    )
    card = result.scalar_one_or_none()
    if not card:
        raise ResourceNotFoundError("Card not found")
    
    # Check organization membership
    org_member_result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == card.column.board.project.organization_id,
            OrganizationMember.user_id == current_user.id
        )
    )
    if not org_member_result.scalar_one_or_none():
        raise InsufficientPermissionsError("Access denied")
    
    # Get checklist items
    items_result = await db.execute(
        select(ChecklistItem).where(ChecklistItem.card_id == card_id)
    )
    items = items_result.scalars().all()
    
    total_items = len(items)
    completed_items = sum(1 for item in items if item.completed)
    ai_generated_count = sum(1 for item in items if item.ai_generated)
    progress_percentage = (completed_items / total_items * 100) if total_items > 0 else 0
    
    return ChecklistProgressResponse(
        total_items=total_items,
        completed_items=completed_items,
        progress_percentage=round(progress_percentage, 2),
        ai_generated_count=ai_generated_count
    )


@router.post("/assignments/validate", response_model=ChecklistValidationResponse)
async def validate_task_assignment(
    request: ChecklistValidationRequest,
    organization_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Validate task assignment permissions"""
    validation_result = await role_permissions.validate_task_assignment(
        db=db,
        organization_id=organization_id,
        current_user=current_user,
        target_user_ids=request.assigned_to
    )

    response_data = {
        'valid': validation_result['valid']
    }

    if not validation_result['valid']:
        response_data.update({
            'error': validation_result.get('error'),
            'error_code': validation_result.get('error_code'),
            'invalid_users': validation_result.get('invalid_users')
        })

    return ChecklistValidationResponse(**response_data)


@router.get("/organizations/{organization_id}/assignable-members", response_model=AssignableMembersResponse)
async def get_assignable_members(
    organization_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get members that current user can assign tasks to"""
    # Get current user's role in organization
    org_member_result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.user_id == current_user.id
        )
    )
    org_member = org_member_result.scalar_one_or_none()

    if not org_member:
        raise InsufficientPermissionsError("User is not a member of this organization")

    # Get assignable members
    assignable_members = await role_permissions.get_assignable_members(
        db=db,
        organization_id=organization_id,
        user_role=org_member.role,
        current_user_id=str(current_user.id)
    )

    permissions = role_permissions.get_role_permissions(org_member.role)

    return AssignableMembersResponse(
        members=assignable_members,
        total_count=len(assignable_members),
        user_role=org_member.role,
        assignment_scope=permissions['assignment_scope']
    )


@router.get("/permissions/role/{role}", response_model=RolePermissionsResponse)
async def get_role_permissions_info(
    role: str,
    current_user: User = Depends(get_current_active_user)
):
    """Get role permissions information"""
    permissions = role_permissions.get_role_permissions(role)
    restriction_message = role_permissions.get_assignment_restriction_message(role)

    return RolePermissionsResponse(
        can_assign_tasks_to_self=permissions['can_assign_tasks_to_self'],
        can_assign_tasks_to_others=permissions['can_assign_tasks_to_others'],
        can_create_tasks=permissions['can_create_tasks'],
        can_edit_own_tasks=permissions['can_edit_own_tasks'],
        can_edit_other_tasks=permissions['can_edit_other_tasks'],
        can_delete_tasks=permissions['can_delete_tasks'],
        assignment_scope=permissions['assignment_scope'],
        restriction_message=restriction_message
    )
