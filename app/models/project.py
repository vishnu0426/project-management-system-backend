"""
Project model
"""
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Date, JSON, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from app.core.database import Base


class Project(Base):
    __tablename__ = "projects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(50), default='active', nullable=False)
    priority = Column(String(20), default='medium', nullable=False)
    start_date = Column(Date, nullable=True)
    due_date = Column(Date, nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Enhanced project fields
    configuration = Column(JSON, nullable=True)  # Project configuration data
    overview = Column(JSON, nullable=True)  # Project overview data
    tech_stack = Column(JSON, nullable=True)  # Technology stack data
    workflow = Column(JSON, nullable=True)  # Workflow and phases data
    tasks = Column(JSON, nullable=True)  # Enhanced tasks data
    notifications = Column(JSON, nullable=True)  # Notification preferences
    launch_options = Column(JSON, nullable=True)  # Launch configuration
    finalized_at = Column(DateTime(timezone=True), nullable=True)  # When project was finalized

    # Project Sign-off and Data Protection Fields
    sign_off_requested = Column(Boolean, default=False, nullable=False)  # Whether sign-off has been requested
    sign_off_requested_at = Column(DateTime(timezone=True), nullable=True)  # When sign-off was requested
    sign_off_requested_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)  # Who requested sign-off
    sign_off_approved = Column(Boolean, default=False, nullable=False)  # Whether project has been signed off
    sign_off_approved_at = Column(DateTime(timezone=True), nullable=True)  # When project was signed off
    sign_off_approved_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)  # Who approved sign-off
    sign_off_notes = Column(Text, nullable=True)  # Notes from the approver
    data_protected = Column(Boolean, default=False, nullable=False)  # Whether data is protected from deletion
    protection_reason = Column(String(255), nullable=True)  # Reason for data protection
    archived_at = Column(DateTime(timezone=True), nullable=True)  # When project was archived
    archived_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)  # Who archived the project

    # Relationships
    organization = relationship("Organization")
    creator = relationship("User", foreign_keys=[created_by])
    sign_off_requester = relationship("User", foreign_keys=[sign_off_requested_by])
    sign_off_approver = relationship("User", foreign_keys=[sign_off_approved_by])
    archiver = relationship("User", foreign_keys=[archived_by])
    boards = relationship("Board", back_populates="project", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Project(id={self.id}, name={self.name})>"
