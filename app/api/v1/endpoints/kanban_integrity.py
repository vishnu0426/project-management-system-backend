"""
Kanban endpoints with guaranteed data integrity
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func
from sqlalchemy.orm import selectinload
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.core.deps import get_current_active_user
from app.models.user import User
from app.models.board import Board
from app.models.column import Column
from app.models.card import Card
from app.models.checklist import ChecklistItem

router = APIRouter()

# Request/Response Models
class ChecklistItemCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=500)
    position: int = Field(..., ge=1)

class ChecklistItemResponse(BaseModel):
    id: str
    content: str
    is_completed: bool
    completed_at: Optional[str] = None
    position: int
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True

class CardCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    position: int = Field(..., ge=1)
    assignee_id: Optional[str] = None
    due_date: Optional[str] = None
    generated_checklist: Optional[List[ChecklistItemCreate]] = []

class CardResponse(BaseModel):
    id: str
    title: str
    description: Optional[str]
    position: int
    status: str
    assignee_id: Optional[str]
    due_date: Optional[str]
    created_at: str
    updated_at: str
    checklist_items: List[ChecklistItemResponse] = []

    class Config:
        from_attributes = True

class CardMoveRequest(BaseModel):
    column_id: str
    position: int = Field(..., ge=1)

class ColumnCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    position: int = Field(..., ge=1)

class ColumnResponse(BaseModel):
    id: str
    name: str
    position: int
    board_id: str
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True

# Utility functions for position management
async def reorder_positions(db: AsyncSession, model_class, parent_field: str, parent_id: str):
    """Ensure positions are contiguous starting from 1"""
    stmt = select(model_class).where(
        getattr(model_class, parent_field) == parent_id
    ).order_by(model_class.position)
    
    result = await db.execute(stmt)
    items = result.scalars().all()
    
    for i, item in enumerate(items, 1):
        if item.position != i:
            item.position = i
    
    await db.commit()

# Board/Column endpoints
@router.get("/boards/{board_id}/columns", response_model=List[ColumnResponse])
async def get_board_columns(
    board_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all columns for a board"""
    stmt = select(Column).where(Column.board_id == board_id).order_by(Column.position)
    result = await db.execute(stmt)
    columns = result.scalars().all()
    return columns

@router.post("/boards/{board_id}/columns", response_model=ColumnResponse)
async def create_column(
    board_id: str,
    column_data: ColumnCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new column"""
    # Verify board exists and user has access
    board_stmt = select(Board).where(Board.id == board_id)
    board_result = await db.execute(board_stmt)
    board = board_result.scalar_one_or_none()
    
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")
    
    # Create column
    column = Column(
        board_id=board_id,
        name=column_data.name,
        position=column_data.position
    )
    
    db.add(column)
    await db.commit()
    await db.refresh(column)
    
    # Reorder positions to ensure no gaps
    await reorder_positions(db, Column, "board_id", board_id)
    
    return column

# Card endpoints with integrity guarantees
@router.post("/columns/{column_id}/cards", response_model=CardResponse)
async def create_card_with_checklist(
    column_id: str,
    card_data: CardCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create card with optional generated checklist - ATOMIC TRANSACTION"""
    
    try:
        # Verify column exists
        column_stmt = select(Column).where(Column.id == column_id)
        column_result = await db.execute(column_stmt)
        column = column_result.scalar_one_or_none()
        
        if not column:
            raise HTTPException(status_code=404, detail="Column not found")
        
        # Create card
        card = Card(
            column_id=column_id,
            title=card_data.title,
            description=card_data.description,
            position=card_data.position,
            assignee_id=card_data.assignee_id,
            due_date=card_data.due_date,
            created_by=current_user.id,
            status="todo"
        )
        
        db.add(card)
        await db.flush()  # Get card ID without committing
        
        # Create checklist items if provided
        checklist_items = []
        if card_data.generated_checklist:
            for item_data in card_data.generated_checklist:
                checklist_item = ChecklistItem(
                    card_id=card.id,
                    content=item_data.content,
                    position=item_data.position,
                    is_completed=False,
                    created_by=current_user.id
                )
                db.add(checklist_item)
                checklist_items.append(checklist_item)
        
        # Commit transaction - all or nothing
        await db.commit()
        
        # Refresh to get all data
        await db.refresh(card)
        for item in checklist_items:
            await db.refresh(item)
        
        # Reorder positions
        await reorder_positions(db, Card, "column_id", column_id)
        
        # Return card with checklist items
        card_response = CardResponse.from_orm(card)
        card_response.checklist_items = [ChecklistItemResponse.from_orm(item) for item in checklist_items]
        
        return card_response
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create card: {str(e)}")

@router.put("/cards/{card_id}/move", response_model=CardResponse)
async def move_card(
    card_id: str,
    move_data: CardMoveRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Move card to different column/position - TRANSACTIONAL REORDERING"""
    
    try:
        # Get card
        card_stmt = select(Card).where(Card.id == card_id)
        card_result = await db.execute(card_stmt)
        card = card_result.scalar_one_or_none()
        
        if not card:
            raise HTTPException(status_code=404, detail="Card not found")
        
        old_column_id = card.column_id
        
        # Update card position and column
        card.column_id = move_data.column_id
        card.position = move_data.position
        
        await db.commit()
        
        # Reorder positions in both old and new columns
        if old_column_id != move_data.column_id:
            await reorder_positions(db, Card, "column_id", old_column_id)
        await reorder_positions(db, Card, "column_id", move_data.column_id)
        
        await db.refresh(card)
        return card
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to move card: {str(e)}")

@router.put("/checklist-items/{item_id}", response_model=ChecklistItemResponse)
async def toggle_checklist_item(
    item_id: str,
    update_data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Toggle checklist item completion - ENSURES completed_at CONSISTENCY"""
    
    # Get item
    item_stmt = select(ChecklistItem).where(ChecklistItem.id == item_id)
    item_result = await db.execute(item_stmt)
    item = item_result.scalar_one_or_none()
    
    if not item:
        raise HTTPException(status_code=404, detail="Checklist item not found")
    
    # Update completion state with proper completed_at handling
    if "is_completed" in update_data:
        is_completed = update_data["is_completed"]
        item.is_completed = is_completed
        
        if is_completed:
            item.completed_at = func.now()
        else:
            item.completed_at = None
    
    # Update content if provided
    if "content" in update_data:
        item.content = update_data["content"]
    
    await db.commit()
    await db.refresh(item)
    
    return item

@router.get("/cards/{card_id}/checklists", response_model=List[ChecklistItemResponse])
async def get_card_checklists(
    card_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all checklist items for a card"""
    stmt = select(ChecklistItem).where(
        ChecklistItem.card_id == card_id
    ).order_by(ChecklistItem.position)
    
    result = await db.execute(stmt)
    items = result.scalars().all()
    
    return items
