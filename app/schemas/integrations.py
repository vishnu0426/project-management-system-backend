"""
Schemas for integration features
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID


class IntegrationCreate(BaseModel):
    integration_type: str = Field(pattern="^(slack|github|google_calendar|outlook|zapier|webhook)$")
    name: str = Field(max_length=255)
    description: Optional[str] = None
    configuration: Dict[str, Any]
    sync_frequency: int = Field(default=300, ge=60)  # Minimum 1 minute


class IntegrationUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    configuration: Optional[Dict[str, Any]] = None
    sync_enabled: Optional[bool] = None
    sync_frequency: Optional[int] = Field(None, ge=60)


class IntegrationResponse(BaseModel):
    id: UUID
    organization_id: UUID
    integration_type: str
    name: str
    description: Optional[str] = None
    status: str
    configuration: Dict[str, Any]
    webhook_url: Optional[str] = None
    sync_enabled: bool
    sync_frequency: int
    last_sync: Optional[datetime] = None
    last_error: Optional[str] = None
    error_count: int
    created_by: UUID
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class WebhookEventResponse(BaseModel):
    id: UUID
    integration_id: Optional[UUID] = None
    organization_id: UUID
    event_type: str
    event_source: str
    payload: Dict[str, Any]
    headers: Optional[Dict[str, Any]] = None
    signature: Optional[str] = None
    status: str
    processing_attempts: int
    last_attempt: Optional[datetime] = None
    error_message: Optional[str] = None
    response_data: Optional[Dict[str, Any]] = None
    created_at: datetime
    processed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class APIKeyCreate(BaseModel):
    key_name: str = Field(max_length=255)
    permissions: List[str]
    rate_limit: int = Field(default=1000, ge=100, le=10000)
    expires_at: Optional[datetime] = None


class APIKeyResponse(BaseModel):
    id: UUID
    organization_id: UUID
    user_id: UUID
    key_name: str
    key_prefix: str
    permissions: List[str]
    rate_limit: int
    is_active: bool
    last_used: Optional[datetime] = None
    usage_count: int
    expires_at: Optional[datetime] = None
    created_at: datetime
    api_key: Optional[str] = None  # Only included when creating new key
    
    class Config:
        from_attributes = True


class ExternalAccountResponse(BaseModel):
    id: UUID
    user_id: UUID
    organization_id: UUID
    provider: str
    provider_user_id: str
    provider_username: Optional[str] = None
    provider_email: Optional[str] = None
    scope: Optional[str] = None
    account_data: Optional[Dict[str, Any]] = None
    is_active: bool
    last_sync: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class IntegrationTemplateResponse(BaseModel):
    id: UUID
    template_name: str
    integration_type: str
    description: Optional[str] = None
    configuration_schema: Dict[str, Any]
    default_configuration: Dict[str, Any]
    required_permissions: Optional[List[str]] = None
    setup_instructions: Optional[str] = None
    is_public: bool
    is_active: bool
    version: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class SlackIntegrationConfig(BaseModel):
    workspace_url: str
    bot_token: str
    signing_secret: str
    default_channel: Optional[str] = None
    notification_types: List[str] = ["task_created", "task_completed", "project_updated"]
    mention_users: bool = True


class GitHubIntegrationConfig(BaseModel):
    repository_url: str
    access_token: str
    webhook_secret: str
    sync_issues: bool = True
    sync_pull_requests: bool = True
    auto_create_tasks: bool = False
    label_mapping: Optional[Dict[str, str]] = None


class CalendarIntegrationConfig(BaseModel):
    provider: str = Field(pattern="^(google|outlook)$")
    calendar_id: str
    access_token: str
    refresh_token: str
    sync_events: bool = True
    create_tasks_from_events: bool = False
    sync_deadlines: bool = True


class WebhookIntegrationConfig(BaseModel):
    webhook_url: str
    secret_token: Optional[str] = None
    events: List[str]
    headers: Optional[Dict[str, str]] = None
    retry_attempts: int = Field(default=3, ge=1, le=10)
    timeout_seconds: int = Field(default=30, ge=5, le=300)


class IntegrationSyncStatus(BaseModel):
    integration_id: UUID
    last_sync: Optional[datetime] = None
    next_sync: Optional[datetime] = None
    status: str
    records_synced: int
    errors: List[str]
    sync_duration_ms: Optional[int] = None


class IntegrationMetrics(BaseModel):
    integration_id: UUID
    total_syncs: int
    successful_syncs: int
    failed_syncs: int
    average_sync_time_ms: float
    last_24h_syncs: int
    error_rate: float
    uptime_percentage: float


class OAuthAuthorizationRequest(BaseModel):
    provider: str = Field(pattern="^(google|microsoft|github|slack)$")
    redirect_uri: str
    scopes: List[str]
    state: Optional[str] = None


class OAuthAuthorizationResponse(BaseModel):
    authorization_url: str
    state: str
    expires_in: int


class OAuthTokenExchange(BaseModel):
    provider: str
    authorization_code: str
    state: str
    redirect_uri: str


class IntegrationHealth(BaseModel):
    integration_id: UUID
    status: str  # healthy, degraded, down
    last_check: datetime
    response_time_ms: Optional[int] = None
    error_message: Optional[str] = None
    uptime_percentage: float
    checks_performed: int
    checks_failed: int
