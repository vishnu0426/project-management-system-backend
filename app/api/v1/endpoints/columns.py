"""
Column management endpoints
"""
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.deps import get_current_active_user
from app.core.exceptions import ResourceNotFoundError, InsufficientPermissionsError
from app.core.permissions import can_create_cards, get_user_role_for_column
from app.models.user import User
from app.models.organization import OrganizationMember
from app.models.board import Board
from app.models.column import Column
from app.schemas.project import ColumnCreate, ColumnUpdate, ColumnResponse, ColumnOrderUpdate
from app.schemas.card import CardCreate, CardResponse, CardAssignmentResponse
from app.models.card import Card, CardAssignment, ChecklistItem
from fastapi import HTTPException

router = APIRouter()


@router.get("/{column_id}", response_model=ColumnResponse)
async def get_column(
    column_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get column by ID"""
    result = await db.execute(
        select(Column)
        .options(selectinload(Column.board).selectinload(Board.project))
        .where(Column.id == column_id)
    )
    column = result.scalar_one_or_none()
    if not column:
        raise ResourceNotFoundError("Column not found")
    
    # Check access
    org_member_result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == column.board.project.organization_id,
            OrganizationMember.user_id == current_user.id
        )
    )
    if not org_member_result.scalar_one_or_none():
        raise InsufficientPermissionsError("Access denied")
    
    return ColumnResponse.from_orm(column)


@router.put("/{column_id}", response_model=ColumnResponse)
async def update_column(
    column_id: str,
    column_data: ColumnUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Update column"""
    result = await db.execute(
        select(Column)
        .options(selectinload(Column.board).selectinload(Board.project))
        .where(Column.id == column_id)
    )
    column = result.scalar_one_or_none()
    if not column:
        raise ResourceNotFoundError("Column not found")
    
    # Check access and permissions
    org_member_result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == column.board.project.organization_id,
            OrganizationMember.user_id == current_user.id
        )
    )
    org_member = org_member_result.scalar_one_or_none()
    if not org_member:
        raise InsufficientPermissionsError("Access denied")
    
    if org_member.role not in ['member', 'admin', 'owner']:
        raise InsufficientPermissionsError("Insufficient permissions")
    
    # Update fields
    if column_data.name is not None:
        column.name = column_data.name
    if column_data.position is not None:
        column.position = column_data.position
    if column_data.color is not None:
        column.color = column_data.color
    
    await db.commit()
    await db.refresh(column)
    
    return ColumnResponse.from_orm(column)


@router.delete("/{column_id}")
async def delete_column(
    column_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete column"""
    result = await db.execute(
        select(Column)
        .options(selectinload(Column.board).selectinload(Board.project))
        .where(Column.id == column_id)
    )
    column = result.scalar_one_or_none()
    if not column:
        raise ResourceNotFoundError("Column not found")
    
    # Check access and permissions
    org_member_result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == column.board.project.organization_id,
            OrganizationMember.user_id == current_user.id
        )
    )
    org_member = org_member_result.scalar_one_or_none()
    if not org_member:
        raise InsufficientPermissionsError("Access denied")
    
    if org_member.role not in ['member', 'admin', 'owner']:
        raise InsufficientPermissionsError("Insufficient permissions")

    # Check if project data is protected
    project = column.board.project
    if project.data_protected:
        # Only owners can delete columns from protected projects
        if org_member.role != 'owner':
            raise HTTPException(
                status_code=403,
                detail=f"Cannot delete column: Project data is protected. Reason: {project.protection_reason or 'Data protection enabled'}"
            )

        # Even owners get a warning about protected data
        if project.sign_off_requested and not project.sign_off_approved:
            raise HTTPException(
                status_code=403,
                detail="Cannot delete column: Project is pending sign-off approval. Complete the sign-off process first."
            )

    await db.delete(column)
    await db.commit()

    return {"success": True, "message": "Column deleted successfully"}


@router.get("/{board_id}/columns", response_model=List[ColumnResponse])
async def get_board_columns(
    board_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get columns for a board"""
    # Check board access
    board_result = await db.execute(
        select(Board)
        .options(selectinload(Board.project))
        .where(Board.id == board_id)
    )
    board = board_result.scalar_one_or_none()
    if not board:
        raise ResourceNotFoundError("Board not found")
    
    # Check organization membership
    org_member_result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == board.project.organization_id,
            OrganizationMember.user_id == current_user.id
        )
    )
    if not org_member_result.scalar_one_or_none():
        raise InsufficientPermissionsError("Access denied")
    
    # Get columns
    result = await db.execute(
        select(Column)
        .where(Column.board_id == board_id)
        .order_by(Column.position)
    )
    columns = result.scalars().all()
    
    return [ColumnResponse.from_orm(column) for column in columns]


# Note: The /boards/{board_id}/columns routes are now handled by aliases in the main router
# to avoid path conflicts. The get_board_columns function is still used by those aliases.


@router.post("/{board_id}/columns", response_model=ColumnResponse)
async def create_column(
    board_id: str,
    column_data: ColumnCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new column"""
    # Check board access
    board_result = await db.execute(
        select(Board)
        .options(selectinload(Board.project))
        .where(Board.id == board_id)
    )
    board = board_result.scalar_one_or_none()
    if not board:
        raise ResourceNotFoundError("Board not found")
    
    # Check organization membership and permissions
    org_member_result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == board.project.organization_id,
            OrganizationMember.user_id == current_user.id
        )
    )
    org_member = org_member_result.scalar_one_or_none()
    if not org_member:
        raise InsufficientPermissionsError("Access denied")
    
    if org_member.role not in ['member', 'admin', 'owner']:
        raise InsufficientPermissionsError("Insufficient permissions")
    
    # Create column
    column = Column(
        board_id=board_id,
        name=column_data.name,
        position=column_data.position,
        color=column_data.color
    )
    
    db.add(column)
    await db.commit()
    await db.refresh(column)
    
    return ColumnResponse.from_orm(column)


# New endpoint: flat column creation
#
# The front‑end calls `POST /api/v1/columns` with a JSON body containing
# `board_id`, `name`, `position`, and optionally `color`.  The original
# column creation endpoint required the board ID to be part of the URL
# (`/columns/{board_id}/columns`).  To support both patterns, this
# handler accepts a payload that includes a `board_id`.  If `board_id`
# is missing, the endpoint returns a 400.
@router.post("", response_model=ColumnResponse)
async def create_column_flat(
    column_data: dict,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new column via a flat endpoint

    This endpoint allows the client to create a column by providing
    both the `board_id` and the column details in the request body.
    It mirrors the functionality of the nested `/columns/{board_id}/columns`
    endpoint but does not require the board ID to appear in the URL.
    """
    # Extract required fields
    board_id = column_data.get("board_id") or column_data.get("boardId")
    name = column_data.get("name")
    position = column_data.get("position")
    color = column_data.get("color")

    # Validate input
    if not board_id:
        raise HTTPException(status_code=400, detail="board_id is required when creating a column via this endpoint")
    if not name or not isinstance(name, str) or not name.strip():
        raise HTTPException(status_code=400, detail="Column name is required and cannot be empty")
    if position is None or not isinstance(position, int) or position < 0:
        raise HTTPException(status_code=400, detail="Column position is required and must be a non‑negative integer")

    # Retrieve the board
    board_result = await db.execute(
        select(Board)
        .options(selectinload(Board.project))
        .where(Board.id == board_id)
    )
    board = board_result.scalar_one_or_none()
    if not board:
        raise ResourceNotFoundError("Board not found")

    # Check organization membership and permissions
    org_member_result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == board.project.organization_id,
            OrganizationMember.user_id == current_user.id
        )
    )
    org_member = org_member_result.scalar_one_or_none()
    if not org_member:
        raise InsufficientPermissionsError("Access denied")
    if org_member.role not in ['member', 'admin', 'owner']:
        raise InsufficientPermissionsError("Insufficient permissions")

    # Create the column
    column = Column(
        board_id=board_id,
        name=name.strip(),
        position=position,
        color=color
    )
    db.add(column)
    await db.commit()
    await db.refresh(column)

    return ColumnResponse.from_orm(column)


@router.put("/{board_id}/columns/order")
async def reorder_columns(
    board_id: str,
    order_data: ColumnOrderUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Reorder columns in a board"""
    # Check board access and permissions
    board_result = await db.execute(
        select(Board)
        .options(selectinload(Board.project))
        .where(Board.id == board_id)
    )
    board = board_result.scalar_one_or_none()
    if not board:
        raise ResourceNotFoundError("Board not found")
    
    org_member_result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == board.project.organization_id,
            OrganizationMember.user_id == current_user.id
        )
    )
    org_member = org_member_result.scalar_one_or_none()
    if not org_member:
        raise InsufficientPermissionsError("Access denied")
    
    if org_member.role not in ['member', 'admin', 'owner']:
        raise InsufficientPermissionsError("Insufficient permissions")
    
    # Update column positions
    for column_order in order_data.column_orders:
        await db.execute(
            update(Column)
            .where(Column.id == column_order["id"], Column.board_id == board_id)
            .values(position=column_order["position"])
        )
    
    await db.commit()
    
    return {"success": True, "message": "Columns reordered successfully"}


@router.get("/{column_id}/cards", response_model=List[CardResponse])
async def get_column_cards(
    column_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all cards in a column"""
    # Check column access
    column_result = await db.execute(
        select(Column)
        .options(
            selectinload(Column.board)
            .selectinload(Board.project)
        )
        .where(Column.id == column_id)
    )
    column = column_result.scalar_one_or_none()
    if not column:
        raise ResourceNotFoundError("Column not found")

    # Check organization membership
    org_member_result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == column.board.project.organization_id,
            OrganizationMember.user_id == current_user.id
        )
    )
    if not org_member_result.scalar_one_or_none():
        raise InsufficientPermissionsError("Access denied")

    # Get cards
    result = await db.execute(
        select(Card)
        .options(selectinload(Card.assignments).selectinload(CardAssignment.user))
        .where(Card.column_id == column_id)
        .order_by(Card.position)
    )
    cards = result.scalars().all()

    # Format response
    response = []
    for card in cards:
        card_response = CardResponse.from_orm(card)
        if card.assignments:
            card_response.assignments = []
            for assignment in card.assignments:
                assignment_data = CardAssignmentResponse.from_orm(assignment)
                assignment_data.user = {
                    "id": str(assignment.user.id),
                    "email": assignment.user.email,
                    "first_name": assignment.user.first_name,
                    "last_name": assignment.user.last_name,
                    "avatar_url": assignment.user.avatar_url
                }
                card_response.assignments.append(assignment_data)
        response.append(card_response)

    return response


@router.post("/{column_id}/cards", response_model=CardResponse)
async def create_column_card(
    column_id: str,
    card_data: CardCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new card in a column"""
    try:
        # Check column access
        column_result = await db.execute(
            select(Column)
            .options(
                selectinload(Column.board)
                .selectinload(Board.project)
            )
            .where(Column.id == column_id)
        )
        column = column_result.scalar_one_or_none()
        if not column:
            raise ResourceNotFoundError("Column not found")

        # Check permissions using the new permission system
        user_role = await get_user_role_for_column(current_user.id, column_id, db)
        if not user_role:
            raise InsufficientPermissionsError("Access denied - user is not a member of this organization")
        if not can_create_cards(user_role):
            raise InsufficientPermissionsError(f"Role '{user_role}' does not have permission to create cards")

        # Get next position
        position_result = await db.execute(
            select(Card.position)
            .where(Card.column_id == column_id)
            .order_by(Card.position.desc())
            .limit(1)
        )
        max_position = position_result.scalar_one_or_none()
        next_position = (max_position or 0) + 1

        # Create card
        card = Card(
            column_id=column_id,
            title=card_data.title,
            description=card_data.description or "",
            priority=card_data.priority or "medium",
            due_date=card_data.due_date,
            position=next_position,
            created_by=current_user.id
        )

        db.add(card)
        await db.flush()  # Get the ID before commit

        # Handle assignments if provided
        if card_data.assigned_to:
            for user_id in card_data.assigned_to:
                try:
                    assignment = CardAssignment(
                        card_id=card.id,
                        user_id=user_id,
                        assigned_by=current_user.id
                    )
                    db.add(assignment)
                except Exception as e:
                    print(f"Warning: Failed to assign user {user_id}: {e}")

        # Handle checklist items if provided
        if card_data.checklist:
            for i, item_data in enumerate(card_data.checklist):
                try:
                    checklist_item = ChecklistItem(
                        card_id=card.id,
                        text=item_data.get('text', ''),
                        position=item_data.get('position', i),
                        ai_generated=item_data.get('ai_generated', False),
                        confidence=item_data.get('confidence'),
                        # ChecklistItem expects ``ai_metadata`` field.
                        ai_metadata=item_data.get('metadata'),
                        created_by=current_user.id
                    )
                    db.add(checklist_item)
                except Exception as e:
                    print(f"Warning: Failed to add checklist item: {e}")

        await db.commit()
        await db.refresh(card)

        # Construct response
        return CardResponse(
            id=card.id,
            column_id=card.column_id,
            title=card.title,
            description=card.description,
            position=card.position,
            priority=card.priority,
            due_date=card.due_date,
            created_by=card.created_by,
            created_at=card.created_at,
            updated_at=card.updated_at,
            assignments=[],
            checklist_items=[]
        )

    except Exception as e:
        await db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to create card: {str(e)}")
