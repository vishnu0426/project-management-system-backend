"""
Bulk operations models for user management and data operations
"""
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, CheckConstraint, Integer
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from app.core.database import Base


class BulkUserOperation(Base):
    __tablename__ = "bulk_user_operations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    operation_type = Column(String(50), nullable=False)  # import, export, bulk_invite, bulk_update, bulk_delete
    status = Column(String(50), default='pending', nullable=False)  # pending, processing, completed, failed, cancelled
    file_path = Column(String(500), nullable=True)  # Path to uploaded/generated file
    file_name = Column(String(255), nullable=True)  # Original filename
    total_records = Column(Integer, default=0, nullable=False)
    processed_records = Column(Integer, default=0, nullable=False)
    successful_records = Column(Integer, default=0, nullable=False)
    failed_records = Column(Integer, default=0, nullable=False)
    error_details = Column(JSON, nullable=True)  # Detailed error information
    result_data = Column(JSON, nullable=True)  # Operation results and statistics
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Constraints
    __table_args__ = (
        CheckConstraint("operation_type IN ('import', 'export', 'bulk_invite', 'bulk_update', 'bulk_delete')", name='valid_operation_type'),
        CheckConstraint("status IN ('pending', 'processing', 'completed', 'failed', 'cancelled')", name='valid_operation_status'),
    )

    # Relationships
    organization = relationship("Organization")
    creator = relationship("User", foreign_keys=[created_by])

    def __repr__(self):
        return f"<BulkUserOperation(id={self.id}, type={self.operation_type}, status={self.status})>"


class BulkOperationLog(Base):
    __tablename__ = "bulk_operation_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bulk_operation_id = Column(UUID(as_uuid=True), ForeignKey('bulk_user_operations.id', ondelete='CASCADE'), nullable=False)
    record_index = Column(Integer, nullable=False)  # Row number in the file
    record_data = Column(JSON, nullable=True)  # Original record data
    operation_result = Column(String(50), nullable=False)  # success, failed, skipped
    error_message = Column(Text, nullable=True)  # Error details if failed
    created_user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)  # If user was created
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Constraints
    __table_args__ = (
        CheckConstraint("operation_result IN ('success', 'failed', 'skipped')", name='valid_operation_result'),
    )

    # Relationships
    bulk_operation = relationship("BulkUserOperation")
    created_user = relationship("User", foreign_keys=[created_user_id])

    def __repr__(self):
        return f"<BulkOperationLog(operation_id={self.bulk_operation_id}, result={self.operation_result})>"


class OrganizationTemplate(Base):
    __tablename__ = "organization_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    template_type = Column(String(50), nullable=False)  # startup, agency, enterprise, custom
    industry = Column(String(100), nullable=True)
    configuration = Column(JSON, nullable=False)  # Template configuration data
    default_roles = Column(JSON, nullable=True)  # Default role structure
    default_projects = Column(JSON, nullable=True)  # Default project templates
    default_workflows = Column(JSON, nullable=True)  # Default workflow settings
    is_public = Column(String(10), default='false', nullable=False)  # public, private, organization
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id'), nullable=True)  # If private template
    usage_count = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Constraints
    __table_args__ = (
        CheckConstraint("template_type IN ('startup', 'agency', 'enterprise', 'custom')", name='valid_template_type'),
        CheckConstraint("is_public IN ('public', 'private', 'organization')", name='valid_visibility'),
    )

    # Relationships
    creator = relationship("User", foreign_keys=[created_by])
    organization = relationship("Organization", foreign_keys=[organization_id])

    def __repr__(self):
        return f"<OrganizationTemplate(id={self.id}, name={self.name}, type={self.template_type})>"
