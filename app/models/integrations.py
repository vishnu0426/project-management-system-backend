"""
Integration models for third-party services
"""
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Boolean, Integer
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from app.core.database import Base


class Integration(Base):
    __tablename__ = "integrations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    integration_type = Column(String(50), nullable=False)  # slack, github, google_calendar, outlook, etc.
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(50), default='inactive', nullable=False)  # active, inactive, error, pending
    configuration = Column(JSON, nullable=False)  # Integration-specific configuration
    credentials = Column(JSON, nullable=True)  # Encrypted credentials
    webhook_url = Column(String(500), nullable=True)  # Webhook endpoint for this integration
    webhook_secret = Column(String(255), nullable=True)  # Webhook verification secret
    sync_enabled = Column(Boolean, default=True, nullable=False)
    sync_frequency = Column(Integer, default=300, nullable=False)  # Sync frequency in seconds
    last_sync = Column(DateTime(timezone=True), nullable=True)
    last_error = Column(Text, nullable=True)
    error_count = Column(Integer, default=0, nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    organization = relationship("Organization")
    creator = relationship("User", foreign_keys=[created_by])
    sync_logs = relationship("IntegrationSyncLog", back_populates="integration", cascade="all, delete-orphan")
    webhooks = relationship("WebhookEvent", back_populates="integration", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Integration(id={self.id}, type={self.integration_type}, status={self.status})>"


class IntegrationSyncLog(Base):
    __tablename__ = "integration_sync_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    integration_id = Column(UUID(as_uuid=True), ForeignKey('integrations.id', ondelete='CASCADE'), nullable=False)
    sync_type = Column(String(50), nullable=False)  # full, incremental, webhook
    status = Column(String(50), nullable=False)  # success, error, partial
    records_processed = Column(Integer, default=0, nullable=False)
    records_created = Column(Integer, default=0, nullable=False)
    records_updated = Column(Integer, default=0, nullable=False)
    records_failed = Column(Integer, default=0, nullable=False)
    sync_data = Column(JSON, nullable=True)  # Sync details and metadata
    error_details = Column(JSON, nullable=True)  # Error information
    duration_ms = Column(Integer, nullable=True)  # Sync duration in milliseconds
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    integration = relationship("Integration", back_populates="sync_logs")

    def __repr__(self):
        return f"<IntegrationSyncLog(id={self.id}, integration_id={self.integration_id}, status={self.status})>"


class WebhookEvent(Base):
    __tablename__ = "webhook_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    integration_id = Column(UUID(as_uuid=True), ForeignKey('integrations.id', ondelete='CASCADE'), nullable=True)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    event_type = Column(String(100), nullable=False)  # task_created, project_updated, etc.
    event_source = Column(String(50), nullable=False)  # internal, slack, github, etc.
    payload = Column(JSON, nullable=False)  # Event payload data
    headers = Column(JSON, nullable=True)  # Request headers
    signature = Column(String(255), nullable=True)  # Webhook signature for verification
    status = Column(String(50), default='pending', nullable=False)  # pending, processed, failed, ignored
    processing_attempts = Column(Integer, default=0, nullable=False)
    last_attempt = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    response_data = Column(JSON, nullable=True)  # Response from webhook processing
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    processed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    integration = relationship("Integration", back_populates="webhooks")
    organization = relationship("Organization")

    def __repr__(self):
        return f"<WebhookEvent(id={self.id}, type={self.event_type}, status={self.status})>"


class APIKey(Base):
    __tablename__ = "api_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    key_name = Column(String(255), nullable=False)
    key_hash = Column(String(255), nullable=False)  # Hashed API key
    key_prefix = Column(String(20), nullable=False)  # First few characters for identification
    permissions = Column(JSON, nullable=False)  # List of allowed permissions
    rate_limit = Column(Integer, default=1000, nullable=False)  # Requests per hour
    is_active = Column(Boolean, default=True, nullable=False)
    last_used = Column(DateTime(timezone=True), nullable=True)
    usage_count = Column(Integer, default=0, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    organization = relationship("Organization")
    user = relationship("User", foreign_keys=[user_id])
    usage_logs = relationship("APIKeyUsage", back_populates="api_key", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<APIKey(id={self.id}, name={self.key_name}, active={self.is_active})>"


class APIKeyUsage(Base):
    __tablename__ = "api_key_usage"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    api_key_id = Column(UUID(as_uuid=True), ForeignKey('api_keys.id', ondelete='CASCADE'), nullable=False)
    endpoint = Column(String(255), nullable=False)
    method = Column(String(10), nullable=False)  # GET, POST, PUT, DELETE
    status_code = Column(Integer, nullable=False)
    response_time_ms = Column(Integer, nullable=True)
    ip_address = Column(String(45), nullable=True)  # IPv4 or IPv6
    user_agent = Column(Text, nullable=True)
    request_size = Column(Integer, nullable=True)  # Request size in bytes
    response_size = Column(Integer, nullable=True)  # Response size in bytes
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    api_key = relationship("APIKey", back_populates="usage_logs")

    def __repr__(self):
        return f"<APIKeyUsage(id={self.id}, endpoint={self.endpoint}, status={self.status_code})>"


class ExternalAccount(Base):
    __tablename__ = "external_accounts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    provider = Column(String(50), nullable=False)  # google, microsoft, github, slack
    provider_user_id = Column(String(255), nullable=False)  # User ID from external provider
    provider_username = Column(String(255), nullable=True)  # Username from external provider
    provider_email = Column(String(255), nullable=True)  # Email from external provider
    access_token = Column(Text, nullable=True)  # Encrypted access token
    refresh_token = Column(Text, nullable=True)  # Encrypted refresh token
    token_expires_at = Column(DateTime(timezone=True), nullable=True)
    scope = Column(String(500), nullable=True)  # OAuth scope granted
    account_data = Column(JSON, nullable=True)  # Additional account information
    is_active = Column(Boolean, default=True, nullable=False)
    last_sync = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    organization = relationship("Organization")

    def __repr__(self):
        return f"<ExternalAccount(id={self.id}, provider={self.provider}, user_id={self.user_id})>"


class IntegrationTemplate(Base):
    __tablename__ = "integration_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    template_name = Column(String(255), nullable=False)
    integration_type = Column(String(50), nullable=False)
    description = Column(Text, nullable=True)
    configuration_schema = Column(JSON, nullable=False)  # JSON schema for configuration
    default_configuration = Column(JSON, nullable=False)  # Default configuration values
    required_permissions = Column(JSON, nullable=True)  # Required OAuth permissions
    setup_instructions = Column(Text, nullable=True)  # Setup instructions for users
    is_public = Column(Boolean, default=True, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    version = Column(String(20), default='1.0.0', nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    creator = relationship("User", foreign_keys=[created_by])

    def __repr__(self):
        return f"<IntegrationTemplate(id={self.id}, name={self.template_name}, type={self.integration_type})>"
