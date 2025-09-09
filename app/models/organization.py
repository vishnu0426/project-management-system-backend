"""
Organization and organization member models
"""
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, CheckConstraint, UniqueConstraint, Boolean, JSON
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from app.core.database import Base


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    domain = Column(String(255), nullable=True)  # Changed from website to domain to match DB
    logo_url = Column(String(500), nullable=True)
    allowed_domains = Column(JSON, nullable=True)

    # Contact information
    contact_email = Column(String(255), nullable=True)
    contact_phone = Column(String(50), nullable=True)

    # Address details
    address_line1 = Column(String(255), nullable=True)
    address_line2 = Column(String(255), nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    postal_code = Column(String(20), nullable=True)
    country = Column(String(100), nullable=True)

    # Organization type/category
    organization_category = Column(String(100), nullable=True)

    # Language preference
    language = Column(String(10), nullable=True)

    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)  # Changed to nullable to match DB
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    creator = relationship("User", foreign_keys=[created_by])
    members = relationship("OrganizationMember", back_populates="organization", cascade="all, delete-orphan")
    settings = relationship("OrganizationSettings", back_populates="organization", uselist=False, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Organization(id={self.id}, name={self.name})>"


class OrganizationMember(Base):
    __tablename__ = "organization_members"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    role = Column(String(50), nullable=False)
    invited_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    joined_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Constraints
    __table_args__ = (
        CheckConstraint("role IN ('viewer', 'member', 'admin', 'owner')", name='valid_role'),
        UniqueConstraint('organization_id', 'user_id', name='unique_org_user'),
    )

    # Relationships
    organization = relationship("Organization", back_populates="members")
    user = relationship("User", foreign_keys=[user_id])
    inviter = relationship("User", foreign_keys=[invited_by])

    def __repr__(self):
        return f"<OrganizationMember(org_id={self.organization_id}, user_id={self.user_id}, role={self.role})>"


class OrganizationCollaboration(Base):
    __tablename__ = "organization_collaborations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    partner_organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    collaboration_type = Column(String(50), default='project_sharing', nullable=False)  # project_sharing, resource_sharing, full_access
    status = Column(String(50), default='pending', nullable=False)  # pending, active, suspended, terminated
    permissions = Column(ARRAY(Text), nullable=True)  # List of specific permissions
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    approved_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)

    # Constraints
    __table_args__ = (
        CheckConstraint("collaboration_type IN ('project_sharing', 'resource_sharing', 'full_access')", name='valid_collaboration_type'),
        CheckConstraint("status IN ('pending', 'active', 'suspended', 'terminated')", name='valid_collaboration_status'),
        CheckConstraint("organization_id != partner_organization_id", name='no_self_collaboration'),
        UniqueConstraint('organization_id', 'partner_organization_id', name='unique_collaboration'),
    )

    # Relationships
    organization = relationship("Organization", foreign_keys=[organization_id])
    partner_organization = relationship("Organization", foreign_keys=[partner_organization_id])
    creator = relationship("User", foreign_keys=[created_by])
    approver = relationship("User", foreign_keys=[approved_by])

    def __repr__(self):
        return f"<OrganizationCollaboration(org_id={self.organization_id}, partner_id={self.partner_organization_id}, status={self.status})>"
