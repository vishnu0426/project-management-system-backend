"""
Card and card assignment models
"""
from sqlalchemy import Column, String, Text, Integer, DateTime, ForeignKey, UniqueConstraint, Boolean, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from app.core.database import Base


class Card(Base):
    __tablename__ = "cards"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    column_id = Column(UUID(as_uuid=True), ForeignKey('columns.id', ondelete='CASCADE'), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    position = Column(Integer, nullable=False)
    priority = Column(String(20), default='medium', nullable=False)
    status = Column(String(20), default='todo', nullable=False)  # todo, in_progress, completed
    due_date = Column(DateTime(timezone=True), nullable=True)
    labels = Column(JSON, nullable=True, default=list)  # List of label strings or objects
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    column = relationship("Column", back_populates="cards")
    creator = relationship("User", foreign_keys=[created_by])
    assignments = relationship("CardAssignment", back_populates="card", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="card", cascade="all, delete-orphan")
    attachments = relationship("Attachment", back_populates="card", cascade="all, delete-orphan")
    checklist_items = relationship("ChecklistItem", back_populates="card", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Card(id={self.id}, title={self.title})>"


class CardAssignment(Base):
    __tablename__ = "card_assignments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    card_id = Column(UUID(as_uuid=True), ForeignKey('cards.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    assigned_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    assigned_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Constraints
    __table_args__ = (
        UniqueConstraint('card_id', 'user_id', name='unique_card_user_assignment'),
    )

    # Relationships
    card = relationship("Card", back_populates="assignments")
    user = relationship("User", foreign_keys=[user_id])
    assigner = relationship("User", foreign_keys=[assigned_by])

    def __repr__(self):
        return f"<CardAssignment(card_id={self.card_id}, user_id={self.user_id})>"


class ChecklistItem(Base):
    __tablename__ = "checklist_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    card_id = Column(UUID(as_uuid=True), ForeignKey('cards.id', ondelete='CASCADE'), nullable=False)
    text = Column(Text, nullable=False)
    completed = Column(Boolean, default=False, nullable=False)
    position = Column(Integer, nullable=False)
    ai_generated = Column(Boolean, default=False, nullable=False)
    confidence = Column(Integer, nullable=True)  # AI confidence score (0-100)
    ai_metadata = Column(JSON, nullable=True)  # Additional metadata
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    card = relationship("Card", back_populates="checklist_items")
    creator = relationship("User", foreign_keys=[created_by])

    def __repr__(self):
        return f"<ChecklistItem(id={self.id}, card_id={self.card_id}, text={self.text[:50]}...)>"
