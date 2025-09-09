"""
Kanban data integrity tests
"""
import pytest
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.user import User
from app.models.organization import Organization
from app.models.board import Board
from app.models.column import Column
from app.models.card import Card
from app.models.checklist import ChecklistItem
from app.api.v1.endpoints.kanban_integrity import (
    create_card_with_checklist,
    move_card,
    toggle_checklist_item,
    CardCreateRequest,
    CardMoveRequest,
    ChecklistItemCreate
)

@pytest.fixture
async def test_data(db_session: AsyncSession):
    """Create test data for Kanban tests"""
    # Create user
    user = User(
        email="test@example.com",
        password_hash="hashed",
        first_name="Test",
        last_name="User"
    )
    db_session.add(user)
    await db_session.flush()
    
    # Create organization
    org = Organization(
        name="Test Org",
        created_by=user.id
    )
    db_session.add(org)
    await db_session.flush()
    
    # Create board
    board = Board(
        name="Test Board",
        organization_id=org.id,
        created_by=user.id
    )
    db_session.add(board)
    await db_session.flush()
    
    # Create columns
    col1 = Column(
        name="Todo",
        board_id=board.id,
        position=1
    )
    col2 = Column(
        name="In Progress", 
        board_id=board.id,
        position=2
    )
    db_session.add_all([col1, col2])
    await db_session.commit()
    
    return {
        'user': user,
        'org': org,
        'board': board,
        'col1': col1,
        'col2': col2
    }

@pytest.mark.asyncio
async def test_create_card_with_generated_checklist_persists_all_items_transactionally(
    db_session: AsyncSession, test_data
):
    """Test that creating a card with checklist items persists everything atomically"""
    
    # Arrange
    user = test_data['user']
    col1 = test_data['col1']
    
    card_request = CardCreateRequest(
        title="Test Card",
        description="Test Description",
        position=1,
        generated_checklist=[
            ChecklistItemCreate(content="Task 1", position=1),
            ChecklistItemCreate(content="Task 2", position=2),
            ChecklistItemCreate(content="Task 3", position=3)
        ]
    )
    
    # Act
    card_response = await create_card_with_checklist(
        column_id=str(col1.id),
        card_data=card_request,
        db=db_session,
        current_user=user
    )
    
    # Assert - Card created
    assert card_response.title == "Test Card"
    assert card_response.description == "Test Description"
    assert len(card_response.checklist_items) == 3
    
    # Assert - Checklist items persisted in DB
    checklist_stmt = select(ChecklistItem).where(ChecklistItem.card_id == card_response.id)
    result = await db_session.execute(checklist_stmt)
    checklist_items = result.scalars().all()
    
    assert len(checklist_items) == 3
    assert all(item.card_id == card_response.id for item in checklist_items)
    assert [item.content for item in sorted(checklist_items, key=lambda x: x.position)] == [
        "Task 1", "Task 2", "Task 3"
    ]

@pytest.mark.asyncio
async def test_toggle_checklist_item_sets_and_clears_completed_at(
    db_session: AsyncSession, test_data
):
    """Test that toggling completion properly manages completed_at timestamp"""
    
    # Arrange
    user = test_data['user']
    col1 = test_data['col1']
    
    # Create card with checklist
    card_request = CardCreateRequest(
        title="Test Card",
        position=1,
        generated_checklist=[
            ChecklistItemCreate(content="Test Task", position=1)
        ]
    )
    
    card_response = await create_card_with_checklist(
        column_id=str(col1.id),
        card_data=card_request,
        db=db_session,
        current_user=user
    )
    
    item_id = card_response.checklist_items[0].id
    
    # Act 1 - Mark as completed
    completed_item = await toggle_checklist_item(
        item_id=item_id,
        update_data={"is_completed": True},
        db=db_session,
        current_user=user
    )
    
    # Assert 1 - Completed
    assert completed_item.is_completed is True
    assert completed_item.completed_at is not None
    
    # Act 2 - Mark as incomplete
    incomplete_item = await toggle_checklist_item(
        item_id=item_id,
        update_data={"is_completed": False},
        db=db_session,
        current_user=user
    )
    
    # Assert 2 - Incomplete
    assert incomplete_item.is_completed is False
    assert incomplete_item.completed_at is None

@pytest.mark.asyncio
async def test_move_card_reorders_positions_without_gaps(
    db_session: AsyncSession, test_data
):
    """Test that moving cards maintains contiguous position ordering"""
    
    # Arrange
    user = test_data['user']
    col1 = test_data['col1']
    col2 = test_data['col2']
    
    # Create multiple cards in col1
    cards = []
    for i in range(3):
        card_request = CardCreateRequest(
            title=f"Card {i+1}",
            position=i+1
        )
        card = await create_card_with_checklist(
            column_id=str(col1.id),
            card_data=card_request,
            db=db_session,
            current_user=user
        )
        cards.append(card)
    
    # Act - Move middle card to col2
    move_request = CardMoveRequest(
        column_id=str(col2.id),
        position=1
    )
    
    moved_card = await move_card(
        card_id=cards[1].id,
        move_data=move_request,
        db=db_session,
        current_user=user
    )
    
    # Assert - Card moved
    assert moved_card.column_id == str(col2.id)
    assert moved_card.position == 1
    
    # Assert - Positions in col1 are contiguous
    col1_cards_stmt = select(Card).where(Card.column_id == col1.id).order_by(Card.position)
    result = await db_session.execute(col1_cards_stmt)
    col1_cards = result.scalars().all()
    
    assert len(col1_cards) == 2
    assert [card.position for card in col1_cards] == [1, 2]
    
    # Assert - Positions in col2 are contiguous
    col2_cards_stmt = select(Card).where(Card.column_id == col2.id).order_by(Card.position)
    result = await db_session.execute(col2_cards_stmt)
    col2_cards = result.scalars().all()
    
    assert len(col2_cards) == 1
    assert col2_cards[0].position == 1

@pytest.mark.asyncio
async def test_checklist_positions_stay_contiguous_after_item_delete(
    db_session: AsyncSession, test_data
):
    """Test that deleting checklist items maintains position integrity"""
    
    # Arrange
    user = test_data['user']
    col1 = test_data['col1']
    
    card_request = CardCreateRequest(
        title="Test Card",
        position=1,
        generated_checklist=[
            ChecklistItemCreate(content="Task 1", position=1),
            ChecklistItemCreate(content="Task 2", position=2),
            ChecklistItemCreate(content="Task 3", position=3),
            ChecklistItemCreate(content="Task 4", position=4)
        ]
    )
    
    card_response = await create_card_with_checklist(
        column_id=str(col1.id),
        card_data=card_request,
        db=db_session,
        current_user=user
    )
    
    # Act - Delete middle item (Task 2)
    middle_item = next(item for item in card_response.checklist_items if item.content == "Task 2")
    
    # Delete via SQL (simulating DELETE endpoint)
    from sqlalchemy import delete
    delete_stmt = delete(ChecklistItem).where(ChecklistItem.id == middle_item.id)
    await db_session.execute(delete_stmt)
    await db_session.commit()
    
    # Reorder positions (this would be called by the delete endpoint)
    from app.api.v1.endpoints.kanban_integrity import reorder_positions
    await reorder_positions(db_session, ChecklistItem, "card_id", card_response.id)
    
    # Assert - Positions are contiguous
    remaining_stmt = select(ChecklistItem).where(
        ChecklistItem.card_id == card_response.id
    ).order_by(ChecklistItem.position)
    result = await db_session.execute(remaining_stmt)
    remaining_items = result.scalars().all()
    
    assert len(remaining_items) == 3
    assert [item.position for item in remaining_items] == [1, 2, 3]
    assert [item.content for item in remaining_items] == ["Task 1", "Task 3", "Task 4"]

@pytest.mark.asyncio
async def test_invalid_payloads_return_422(db_session: AsyncSession, test_data):
    """Test that invalid payloads are properly validated"""
    
    user = test_data['user']
    col1 = test_data['col1']
    
    # Test invalid card creation
    with pytest.raises(Exception):  # Should raise validation error
        invalid_request = CardCreateRequest(
            title="",  # Empty title should fail
            position=-1  # Negative position should fail
        )
        await create_card_with_checklist(
            column_id=str(col1.id),
            card_data=invalid_request,
            db=db_session,
            current_user=user
        )
