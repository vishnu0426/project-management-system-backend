"""
Comprehensive Kanban Board Service
Handles all board, column, and card operations with proper data persistence
"""
import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func
from sqlalchemy.orm import selectinload

from app.models.project import Project
from app.models.board import Board
from app.models.column import Column as ColumnModel
from app.models.card import Card, CardAssignment, ChecklistItem
from app.models.user import User
from app.models.organization import OrganizationMember
from app.core.exceptions import ResourceNotFoundError, InsufficientPermissionsError


class KanbanService:
    """Service for managing Kanban boards, columns, and cards"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_or_create_project_board(
        self, 
        project_id: str, 
        user_id: str,
        board_name: str = "Project Management Board"
    ) -> Board:
        """Get existing board for project or create a new one with default columns"""
        
        # Check if project exists and user has access
        project_result = await self.db.execute(
            select(Project).where(Project.id == project_id)
        )
        project = project_result.scalar_one_or_none()
        if not project:
            raise ResourceNotFoundError("Project not found")
        
        # Check user permissions
        org_member_result = await self.db.execute(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == project.organization_id,
                OrganizationMember.user_id == user_id
            )
        )
        org_member = org_member_result.scalar_one_or_none()
        if not org_member:
            raise InsufficientPermissionsError("Access denied")
        
        # Check if board already exists
        board_result = await self.db.execute(
            select(Board).where(Board.project_id == project_id)
        )
        existing_board = board_result.scalar_one_or_none()
        
        if existing_board:
            return existing_board
        
        # Create new board
        board = Board(
            project_id=project_id,
            name=board_name,
            description=f"Kanban board for {project.name}",
            created_by=user_id
        )
        
        self.db.add(board)
        await self.db.flush()  # Get the board ID
        
        # Create default columns
        default_columns = [
            {"name": "To-Do", "position": 0, "color": "#E5E7EB"},
            {"name": "In Progress", "position": 1, "color": "#DBEAFE"},
            {"name": "Review", "position": 2, "color": "#FEF3C7"},
            {"name": "Done", "position": 3, "color": "#D1FAE5"},
        ]

        for col_data in default_columns:
            column = ColumnModel(
                board_id=board.id,
                name=col_data["name"],
                position=col_data["position"],
                color=col_data["color"]
            )
            self.db.add(column)
        
        await self.db.commit()
        await self.db.refresh(board)
        
        return board
    
    async def get_board_with_columns(self, board_id: str, user_id: str) -> Dict[str, Any]:
        """Get board with all its columns and verify user access"""
        
        board_result = await self.db.execute(
            select(Board)
            .options(
                selectinload(Board.project),
                selectinload(Board.columns).selectinload(ColumnModel.cards)
            )
            .where(Board.id == board_id)
        )
        board = board_result.scalar_one_or_none()
        if not board:
            raise ResourceNotFoundError("Board not found")
        
        # Check user permissions
        org_member_result = await self.db.execute(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == board.project.organization_id,
                OrganizationMember.user_id == user_id
            )
        )
        org_member = org_member_result.scalar_one_or_none()
        if not org_member:
            raise InsufficientPermissionsError("Access denied")
        
        # Sort columns by position
        columns = sorted(board.columns, key=lambda x: x.position)
        
        return {
            "id": str(board.id),
            "name": board.name,
            "description": board.description,
            "project_id": str(board.project_id),
            "columns": [
                {
                    "id": str(col.id),
                    "name": col.name,
                    "position": col.position,
                    "color": col.color,
                    "board_id": str(col.board_id),
                    "cards": [
                        {
                            "id": str(card.id),
                            "title": card.title,
                            "description": card.description,
                            "priority": card.priority,
                            "status": card.status,
                            "position": card.position,
                            "column_id": str(card.column_id),
                            "created_by": str(card.created_by),
                            "created_at": card.created_at.isoformat(),
                            "updated_at": card.updated_at.isoformat(),
                            "due_date": card.due_date.isoformat() if card.due_date else None,
                            "labels": card.labels or []
                        }
                        for card in sorted(col.cards, key=lambda x: x.position)
                    ]
                }
                for col in columns
            ],
            "created_at": board.created_at.isoformat(),
            "updated_at": board.updated_at.isoformat()
        }
    
    async def create_column(
        self, 
        board_id: str, 
        user_id: str, 
        name: str, 
        color: str = "#E5E7EB"
    ) -> Dict[str, Any]:
        """Create a new column in a board"""
        
        # Verify board exists and user has access
        board_result = await self.db.execute(
            select(Board)
            .options(selectinload(Board.project))
            .where(Board.id == board_id)
        )
        board = board_result.scalar_one_or_none()
        if not board:
            raise ResourceNotFoundError("Board not found")
        
        # Check user permissions
        org_member_result = await self.db.execute(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == board.project.organization_id,
                OrganizationMember.user_id == user_id
            )
        )
        org_member = org_member_result.scalar_one_or_none()
        if not org_member:
            raise InsufficientPermissionsError("Access denied")
        
        # Get next position
        max_position_result = await self.db.execute(
            select(func.max(ColumnModel.position)).where(ColumnModel.board_id == board_id)
        )
        max_position = max_position_result.scalar_one_or_none() or -1

        # Create column
        column = ColumnModel(
            board_id=board_id,
            name=name,
            position=max_position + 1,
            color=color
        )
        
        self.db.add(column)
        await self.db.commit()
        await self.db.refresh(column)
        
        return {
            "id": str(column.id),
            "name": column.name,
            "position": column.position,
            "color": column.color,
            "board_id": str(column.board_id),
            "created_at": column.created_at.isoformat(),
            "updated_at": column.updated_at.isoformat()
        }
    
    async def get_column_cards(self, column_id: str, user_id: str) -> List[Dict[str, Any]]:
        """Get all cards in a column with user access verification"""
        
        # Verify column exists and user has access
        column_result = await self.db.execute(
            select(ColumnModel)
            .options(
                selectinload(ColumnModel.board).selectinload(Board.project)
            )
            .where(ColumnModel.id == column_id)
        )
        column = column_result.scalar_one_or_none()
        if not column:
            raise ResourceNotFoundError("Column not found")
        
        # Check user permissions
        org_member_result = await self.db.execute(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == column.board.project.organization_id,
                OrganizationMember.user_id == user_id
            )
        )
        org_member = org_member_result.scalar_one_or_none()
        if not org_member:
            raise InsufficientPermissionsError("Access denied")
        
        # Get cards
        cards_result = await self.db.execute(
            select(Card)
            .options(
                selectinload(Card.assignments).selectinload(CardAssignment.user),
                selectinload(Card.checklist_items)
            )
            .where(Card.column_id == column_id)
            .order_by(Card.position)
        )
        cards = cards_result.scalars().all()
        
        return [
            {
                "id": str(card.id),
                "column_id": str(card.column_id),
                "title": card.title,
                "description": card.description,
                "position": card.position,
                "priority": card.priority,
                "status": card.status,
                "due_date": card.due_date.isoformat() if card.due_date else None,
                "labels": card.labels or [],
                "created_by": str(card.created_by),
                "created_at": card.created_at.isoformat(),
                "updated_at": card.updated_at.isoformat(),
                "assignments": [
                    {
                        "user_id": str(assignment.user_id),
                        "user_name": assignment.user.full_name if assignment.user else "Unknown",
                        "assigned_at": assignment.assigned_at.isoformat()
                    }
                    for assignment in card.assignments
                ],
                "checklist_items": [
                    {
                        "id": str(item.id),
                        "text": item.text,
                        "completed": item.completed,
                        "position": item.position
                    }
                    for item in card.checklist_items
                ]
            }
            for card in cards
        ]

    async def create_card(
        self,
        column_id: str,
        user_id: str,
        title: str,
        description: str = "",
        priority: str = "medium",
        assigned_to: Optional[List[str]] = None,
        due_date: Optional[datetime] = None,
        labels: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Create a new card in a column"""

        # Verify column exists and user has access
        column_result = await self.db.execute(
            select(ColumnModel)
            .options(
                selectinload(ColumnModel.board).selectinload(Board.project)
            )
            .where(ColumnModel.id == column_id)
        )
        column = column_result.scalar_one_or_none()
        if not column:
            raise ResourceNotFoundError("Column not found")

        # Check user permissions
        org_member_result = await self.db.execute(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == column.board.project.organization_id,
                OrganizationMember.user_id == user_id
            )
        )
        org_member = org_member_result.scalar_one_or_none()
        if not org_member:
            raise InsufficientPermissionsError("Access denied")

        # Get next position in column
        max_position_result = await self.db.execute(
            select(func.max(Card.position)).where(Card.column_id == column_id)
        )
        max_position = max_position_result.scalar_one_or_none() or -1

        # Create card
        card = Card(
            column_id=column_id,
            title=title,
            description=description,
            position=max_position + 1,
            priority=priority,
            status="todo",
            due_date=due_date,
            labels=labels or [],
            created_by=user_id
        )

        self.db.add(card)
        await self.db.flush()  # Get the card ID

        # Add assignments if provided
        if assigned_to:
            for assignee_id in assigned_to:
                # Verify assignee exists and is in the organization
                assignee_result = await self.db.execute(
                    select(OrganizationMember).where(
                        OrganizationMember.organization_id == column.board.project.organization_id,
                        OrganizationMember.user_id == assignee_id
                    )
                )
                if assignee_result.scalar_one_or_none():
                    assignment = CardAssignment(
                        card_id=card.id,
                        user_id=assignee_id,
                        assigned_by=user_id
                    )
                    self.db.add(assignment)

        await self.db.commit()
        await self.db.refresh(card)

        # Return card with assignments
        card_with_assignments = await self.db.execute(
            select(Card)
            .options(
                selectinload(Card.assignments).selectinload(CardAssignment.user)
            )
            .where(Card.id == card.id)
        )
        card = card_with_assignments.scalar_one()

        return {
            "id": str(card.id),
            "column_id": str(card.column_id),
            "title": card.title,
            "description": card.description,
            "position": card.position,
            "priority": card.priority,
            "status": card.status,
            "due_date": card.due_date.isoformat() if card.due_date else None,
            "labels": card.labels or [],
            "created_by": str(card.created_by),
            "created_at": card.created_at.isoformat(),
            "updated_at": card.updated_at.isoformat(),
            "assignments": [
                {
                    "user_id": str(assignment.user_id),
                    "user_name": assignment.user.full_name if assignment.user else "Unknown",
                    "assigned_at": assignment.assigned_at.isoformat()
                }
                for assignment in card.assignments
            ]
        }

    async def move_card(
        self,
        card_id: str,
        target_column_id: str,
        user_id: str,
        position: Optional[int] = None
    ) -> Dict[str, Any]:
        """Move a card to a different column and/or position"""

        # Get card with current column info
        card_result = await self.db.execute(
            select(Card)
            .options(
                selectinload(Card.column)
                .selectinload(ColumnModel.board)
                .selectinload(Board.project)
            )
            .where(Card.id == card_id)
        )
        card = card_result.scalar_one_or_none()
        if not card:
            raise ResourceNotFoundError("Card not found")

        # Get target column
        target_column_result = await self.db.execute(
            select(ColumnModel)
            .options(
                selectinload(ColumnModel.board).selectinload(Board.project)
            )
            .where(ColumnModel.id == target_column_id)
        )
        target_column = target_column_result.scalar_one_or_none()
        if not target_column:
            raise ResourceNotFoundError("Target column not found")

        # Check user permissions
        org_member_result = await self.db.execute(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == card.column.board.project.organization_id,
                OrganizationMember.user_id == user_id
            )
        )
        org_member = org_member_result.scalar_one_or_none()
        if not org_member:
            raise InsufficientPermissionsError("Access denied")

        # Determine new position
        if position is None:
            max_position_result = await self.db.execute(
                select(func.max(Card.position)).where(Card.column_id == target_column_id)
            )
            max_position = max_position_result.scalar_one_or_none() or -1
            position = max_position + 1

        # Update card
        card.column_id = target_column_id
        card.position = position
        card.updated_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(card)

        return {
            "id": str(card.id),
            "column_id": str(card.column_id),
            "position": card.position,
            "updated_at": card.updated_at.isoformat()
        }

    async def update_card(
        self,
        card_id: str,
        user_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        priority: Optional[str] = None,
        due_date: Optional[datetime] = None,
        labels: Optional[List[Dict[str, Any]]] = None,
        checklist: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Update card details"""

        # Get card with access verification
        card_result = await self.db.execute(
            select(Card)
            .options(
                selectinload(Card.column)
                .selectinload(ColumnModel.board)
                .selectinload(Board.project)
            )
            .where(Card.id == card_id)
        )
        card = card_result.scalar_one_or_none()
        if not card:
            raise ResourceNotFoundError("Card not found")

        # Check user permissions
        org_member_result = await self.db.execute(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == card.column.board.project.organization_id,
                OrganizationMember.user_id == user_id
            )
        )
        org_member = org_member_result.scalar_one_or_none()
        if not org_member:
            raise InsufficientPermissionsError("Access denied")

        # Update fields
        if title is not None:
            card.title = title
        if description is not None:
            card.description = description
        if priority is not None:
            card.priority = priority
        if due_date is not None:
            card.due_date = due_date
        if labels is not None:
            card.labels = labels

        # Handle checklist updates (temporarily disabled to fix 500 error)
        # TODO: Re-enable checklist updates after fixing the database schema issues
        if False and checklist is not None and isinstance(checklist, list):
            try:
                # Delete existing checklist items
                await self.db.execute(delete(ChecklistItem).where(ChecklistItem.card_id == card.id))

                # Add new checklist items
                for item_data in checklist:
                    if isinstance(item_data, dict) and item_data.get('text'):
                        checklist_item = ChecklistItem(
                            card_id=card.id,
                            text=item_data.get('text', ''),
                            position=item_data.get('position', 0),
                            completed=item_data.get('completed', False),
                            ai_generated=item_data.get('ai_generated', False),
                            confidence=item_data.get('confidence'),
                            ai_metadata=item_data.get('metadata'),
                            created_by=uuid.UUID(user_id) if isinstance(user_id, str) else user_id
                        )
                        self.db.add(checklist_item)
            except Exception as e:
                print(f"Error updating checklist: {e}")
                # Continue without failing the entire update

        card.updated_at = datetime.utcnow()

        await self.db.commit()

        # Reload card with checklist items
        card_result = await self.db.execute(
            select(Card)
            .options(selectinload(Card.checklist_items))
            .where(Card.id == card_id)
        )
        updated_card = card_result.scalar_one()

        return {
            "id": str(updated_card.id),
            "title": updated_card.title,
            "description": updated_card.description,
            "priority": updated_card.priority,
            "due_date": updated_card.due_date.isoformat() if updated_card.due_date else None,
            "labels": updated_card.labels or [],
            "checklist_items": [
                {
                    "id": str(item.id),
                    "text": item.text,
                    "position": item.position,
                    "completed": item.completed,
                    "ai_generated": item.ai_generated,
                    "confidence": item.confidence,
                    "metadata": item.ai_metadata,
                    "created_at": item.created_at.isoformat(),
                    "updated_at": item.updated_at.isoformat()
                }
                for item in sorted(updated_card.checklist_items, key=lambda x: x.position)
            ],
            "updated_at": updated_card.updated_at.isoformat()
        }

    async def delete_card(self, card_id: str, user_id: str) -> bool:
        """Delete a card"""

        # Get card with access verification
        card_result = await self.db.execute(
            select(Card)
            .options(
                selectinload(Card.column)
                .selectinload(ColumnModel.board)
                .selectinload(Board.project)
            )
            .where(Card.id == card_id)
        )
        card = card_result.scalar_one_or_none()
        if not card:
            raise ResourceNotFoundError("Card not found")

        # Check user permissions
        org_member_result = await self.db.execute(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == card.column.board.project.organization_id,
                OrganizationMember.user_id == user_id
            )
        )
        org_member = org_member_result.scalar_one_or_none()
        if not org_member:
            raise InsufficientPermissionsError("Access denied")

        # Delete card (cascade will handle assignments, comments, etc.)
        await self.db.execute(delete(Card).where(Card.id == card_id))
        await self.db.commit()

        return True
