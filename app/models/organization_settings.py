"""
Organization Settings Model
Enhanced organization settings for multi-organization management
"""
import uuid
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, JSON, Text, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.core.database import Base


class OrganizationSettings(Base):
    """Organization-specific settings and permissions"""
    __tablename__ = "organization_settings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False, unique=True)
    
    # Project creation permissions
    allow_admin_create_projects = Column(Boolean, default=True, nullable=False)
    allow_member_create_projects = Column(Boolean, default=False, nullable=False)
    
    # Meeting permissions
    allow_admin_schedule_meetings = Column(Boolean, default=True, nullable=False)
    allow_member_schedule_meetings = Column(Boolean, default=False, nullable=False)
    
    # Invitation settings
    require_domain_match = Column(Boolean, default=True, nullable=False)
    allowed_invitation_domains = Column(JSON, nullable=True)  # List of allowed domains
    
    # Notification settings
    enable_task_notifications = Column(Boolean, default=True, nullable=False)
    enable_meeting_notifications = Column(Boolean, default=True, nullable=False)
    enable_role_change_notifications = Column(Boolean, default=True, nullable=False)
    
    # Dashboard customization
    dashboard_config = Column(JSON, nullable=True)
    
    # Security settings
    require_email_verification = Column(Boolean, default=True, nullable=False)
    password_policy = Column(JSON, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    organization = relationship("Organization", back_populates="settings")

    def __repr__(self):
        return f"<OrganizationSettings(org_id={self.organization_id})>"


class UserOrganizationContext(Base):
    """Track user's current organization context for multi-org switching"""
    __tablename__ = "user_organization_contexts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, unique=True)
    current_organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=True)
    last_switched_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Session preferences
    preferences = Column(JSON, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship("User")
    current_organization = relationship("Organization")

    def __repr__(self):
        return f"<UserOrganizationContext(user_id={self.user_id}, org_id={self.current_organization_id})>"


class InvitationToken(Base):
    """Temporary invitation tokens for organization/project invitations"""
    __tablename__ = "invitation_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    token = Column(String(255), nullable=False, unique=True)
    email = Column(String(255), nullable=False)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    project_id = Column(UUID(as_uuid=True), ForeignKey('projects.id', ondelete='CASCADE'), nullable=True)
    invited_role = Column(String(20), nullable=False)  # admin, member
    temporary_password = Column(String(255), nullable=False)  # Hashed temporary password
    
    # Invitation details
    invited_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    invitation_message = Column(Text, nullable=True)
    
    # Status and expiry
    is_used = Column(Boolean, default=False, nullable=False)
    used_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    organization = relationship("Organization")
    project = relationship("Project")
    inviter = relationship("User", foreign_keys=[invited_by])

    def __repr__(self):
        return f"<InvitationToken(email={self.email}, org_id={self.organization_id})>"


class MeetingSchedule(Base):
    """Meeting scheduling system"""
    __tablename__ = "meeting_schedules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    project_id = Column(UUID(as_uuid=True), ForeignKey('projects.id', ondelete='CASCADE'), nullable=True)
    
    # Meeting details
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    meeting_type = Column(String(50), default='team', nullable=False)  # team, individual, project
    
    # Scheduling
    scheduled_at = Column(DateTime(timezone=True), nullable=False)
    duration_minutes = Column(Integer, default=60, nullable=False)
    timezone = Column(String(50), default='UTC', nullable=False)
    
    # Meeting link/details
    meeting_link = Column(String(500), nullable=True)
    meeting_platform = Column(String(50), default='zoom', nullable=False)  # zoom, teams, meet, etc.
    
    # Participants
    organizer_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    participants = Column(JSON, nullable=True)  # List of user IDs
    
    # Status
    status = Column(String(20), default='scheduled', nullable=False)  # scheduled, started, completed, cancelled
    
    # Notifications
    reminder_sent = Column(Boolean, default=False, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    organization = relationship("Organization")
    project = relationship("Project")
    organizer = relationship("User", foreign_keys=[organizer_id])

    def __repr__(self):
        return f"<MeetingSchedule(id={self.id}, title={self.title})>"
