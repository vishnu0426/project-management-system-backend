"""
Security and compliance models
"""
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Boolean, Integer
from sqlalchemy.dialects.postgresql import UUID, JSON, INET
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from app.core.database import Base


class DataRetentionPolicy(Base):
    __tablename__ = "data_retention_policies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    policy_name = Column(String(255), nullable=False)
    data_type = Column(String(100), nullable=False)  # user_data, project_data, activity_logs, etc.
    retention_period_days = Column(Integer, nullable=False)
    auto_delete = Column(Boolean, default=False, nullable=False)
    archive_before_delete = Column(Boolean, default=True, nullable=False)
    legal_basis = Column(String(100), nullable=True)  # GDPR legal basis
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    organization = relationship("Organization")
    creator = relationship("User", foreign_keys=[created_by])

    def __repr__(self):
        return f"<DataRetentionPolicy(id={self.id}, name={self.policy_name}, type={self.data_type})>"


class GDPRRequest(Base):
    __tablename__ = "gdpr_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=True)
    request_type = Column(String(50), nullable=False)  # access, rectification, erasure, portability, restriction
    status = Column(String(50), default='pending', nullable=False)  # pending, processing, completed, rejected
    requester_email = Column(String(255), nullable=False)
    requester_name = Column(String(255), nullable=True)
    request_details = Column(Text, nullable=True)
    verification_method = Column(String(100), nullable=True)
    verification_completed = Column(Boolean, default=False, nullable=False)
    response_data = Column(JSON, nullable=True)  # Data provided in response
    response_file_path = Column(String(500), nullable=True)
    rejection_reason = Column(Text, nullable=True)
    processed_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    due_date = Column(DateTime(timezone=True), nullable=False)  # 30 days from request
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    organization = relationship("Organization")
    user = relationship("User", foreign_keys=[user_id])
    processor = relationship("User", foreign_keys=[processed_by])

    def __repr__(self):
        return f"<GDPRRequest(id={self.id}, type={self.request_type}, status={self.status})>"


class SecurityEvent(Base):
    __tablename__ = "security_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=True)
    event_type = Column(String(100), nullable=False)  # login_failure, suspicious_activity, data_breach, etc.
    severity = Column(String(20), nullable=False)  # low, medium, high, critical
    event_source = Column(String(100), nullable=False)  # api, web, mobile, system
    ip_address = Column(INET, nullable=True)
    user_agent = Column(Text, nullable=True)
    event_data = Column(JSON, nullable=True)  # Additional event details
    risk_score = Column(Integer, nullable=True)  # 0-100 risk assessment
    is_resolved = Column(Boolean, default=False, nullable=False)
    resolved_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    resolution_notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    organization = relationship("Organization")
    user = relationship("User", foreign_keys=[user_id])
    resolver = relationship("User", foreign_keys=[resolved_by])

    def __repr__(self):
        return f"<SecurityEvent(id={self.id}, type={self.event_type}, severity={self.severity})>"


class BackupRecord(Base):
    __tablename__ = "backup_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=True)
    backup_type = Column(String(50), nullable=False)  # full, incremental, differential
    backup_scope = Column(String(50), nullable=False)  # organization, system, database
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=True)  # Size in bytes
    compression_type = Column(String(20), nullable=True)  # gzip, zip, none
    encryption_enabled = Column(Boolean, default=True, nullable=False)
    checksum = Column(String(128), nullable=True)  # SHA-256 checksum
    status = Column(String(50), default='pending', nullable=False)  # pending, running, completed, failed
    error_message = Column(Text, nullable=True)
    retention_until = Column(DateTime(timezone=True), nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    organization = relationship("Organization")
    creator = relationship("User", foreign_keys=[created_by])

    def __repr__(self):
        return f"<BackupRecord(id={self.id}, type={self.backup_type}, status={self.status})>"


class ComplianceAudit(Base):
    __tablename__ = "compliance_audits"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    audit_type = Column(String(50), nullable=False)  # gdpr, soc2, iso27001, internal
    audit_scope = Column(String(100), nullable=False)  # full, partial, specific_area
    status = Column(String(50), default='planned', nullable=False)  # planned, in_progress, completed, failed
    compliance_framework = Column(String(100), nullable=False)
    auditor_name = Column(String(255), nullable=True)
    auditor_organization = Column(String(255), nullable=True)
    findings = Column(JSON, nullable=True)  # Audit findings and recommendations
    compliance_score = Column(Integer, nullable=True)  # 0-100 compliance score
    report_file_path = Column(String(500), nullable=True)
    remediation_plan = Column(JSON, nullable=True)  # Action items for compliance
    next_audit_date = Column(DateTime(timezone=True), nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    organization = relationship("Organization")
    creator = relationship("User", foreign_keys=[created_by])

    def __repr__(self):
        return f"<ComplianceAudit(id={self.id}, type={self.audit_type}, status={self.status})>"


class SecurityAlert(Base):
    __tablename__ = "security_alerts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=True)
    alert_type = Column(String(100), nullable=False)  # brute_force, data_breach, unusual_access, etc.
    severity = Column(String(20), nullable=False)  # low, medium, high, critical
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    affected_resources = Column(JSON, nullable=True)  # List of affected resources
    detection_method = Column(String(100), nullable=False)  # automated, manual, external
    alert_source = Column(String(100), nullable=False)  # system, user_report, external_tool
    status = Column(String(50), default='open', nullable=False)  # open, investigating, resolved, false_positive
    assigned_to = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    escalation_level = Column(Integer, default=1, nullable=False)  # 1-5 escalation levels
    response_actions = Column(JSON, nullable=True)  # Actions taken in response
    resolution_notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    organization = relationship("Organization")
    assignee = relationship("User", foreign_keys=[assigned_to])

    def __repr__(self):
        return f"<SecurityAlert(id={self.id}, type={self.alert_type}, severity={self.severity})>"


class ConsentRecord(Base):
    __tablename__ = "consent_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    consent_type = Column(String(100), nullable=False)  # data_processing, marketing, analytics, etc.
    consent_given = Column(Boolean, nullable=False)
    consent_method = Column(String(50), nullable=False)  # explicit, implicit, opt_in, opt_out
    legal_basis = Column(String(100), nullable=True)  # GDPR Article 6 basis
    purpose_description = Column(Text, nullable=False)
    data_categories = Column(JSON, nullable=True)  # Categories of data covered
    retention_period = Column(String(100), nullable=True)
    third_party_sharing = Column(Boolean, default=False, nullable=False)
    withdrawal_method = Column(String(100), nullable=True)
    ip_address = Column(INET, nullable=True)
    user_agent = Column(Text, nullable=True)
    consent_version = Column(String(20), nullable=False)  # Version of consent form
    expires_at = Column(DateTime(timezone=True), nullable=True)
    withdrawn_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    organization = relationship("Organization")

    def __repr__(self):
        return f"<ConsentRecord(id={self.id}, type={self.consent_type}, given={self.consent_given})>"
