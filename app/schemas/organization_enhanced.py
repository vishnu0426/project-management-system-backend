"""
Enhanced Organization Schemas
Multi-organization management with role-based access control
"""
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID


class OrganizationSettingsCreate(BaseModel):
    allow_admin_create_projects: bool = True
    allow_member_create_projects: bool = False
    allow_admin_schedule_meetings: bool = True
    allow_member_schedule_meetings: bool = False
    require_domain_match: bool = True
    allowed_invitation_domains: Optional[List[str]] = None
    enable_task_notifications: bool = True
    enable_meeting_notifications: bool = True
    enable_role_change_notifications: bool = True
    dashboard_config: Optional[Dict[str, Any]] = None
    require_email_verification: bool = True
    password_policy: Optional[Dict[str, Any]] = None


class OrganizationSettingsUpdate(BaseModel):
    allow_admin_create_projects: Optional[bool] = None
    allow_member_create_projects: Optional[bool] = None
    allow_admin_schedule_meetings: Optional[bool] = None
    allow_member_schedule_meetings: Optional[bool] = None
    require_domain_match: Optional[bool] = None
    allowed_invitation_domains: Optional[List[str]] = None
    enable_task_notifications: Optional[bool] = None
    enable_meeting_notifications: Optional[bool] = None
    enable_role_change_notifications: Optional[bool] = None
    dashboard_config: Optional[Dict[str, Any]] = None
    require_email_verification: Optional[bool] = None
    password_policy: Optional[Dict[str, Any]] = None


class OrganizationSettingsResponse(BaseModel):
    id: UUID
    organization_id: UUID
    allow_admin_create_projects: bool
    allow_member_create_projects: bool
    allow_admin_schedule_meetings: bool
    allow_member_schedule_meetings: bool
    require_domain_match: bool
    allowed_invitation_domains: Optional[List[str]]
    enable_task_notifications: bool
    enable_meeting_notifications: bool
    enable_role_change_notifications: bool
    dashboard_config: Optional[Dict[str, Any]]
    require_email_verification: bool
    password_policy: Optional[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class OrganizationSwitchRequest(BaseModel):
    organization_id: UUID


class UserOrganizationContextResponse(BaseModel):
    id: UUID
    user_id: UUID
    current_organization_id: Optional[UUID]
    last_switched_at: datetime
    preferences: Optional[Dict[str, Any]]

    class Config:
        from_attributes = True


class InvitationRequest(BaseModel):
    email: str = Field(..., pattern=r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    role: str = Field(..., pattern=r'^(admin|member)$')
    project_id: Optional[UUID] = None
    invitation_message: Optional[str] = None

    @validator('email')
    def validate_email(cls, v):
        return v.lower().strip()


class InvitationResponse(BaseModel):
    id: UUID
    token: str
    email: str
    organization_id: UUID
    project_id: Optional[UUID]
    invited_role: str
    invited_by: UUID
    invitation_message: Optional[str]
    expires_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True


class InvitationAcceptRequest(BaseModel):
    token: str
    temporary_password: str
    new_password: str = Field(..., min_length=8)
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)


class MeetingScheduleCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    project_id: Optional[UUID] = None
    meeting_type: str = Field(default='team', pattern=r'^(team|individual|project)$')
    scheduled_at: datetime
    duration_minutes: int = Field(default=60, ge=15, le=480)  # 15 minutes to 8 hours
    timezone: str = Field(default='UTC', max_length=50)
    meeting_platform: str = Field(default='zoom', pattern=r'^(zoom|teams|meet|custom)$')
    meeting_link: Optional[str] = Field(None, max_length=500)
    participants: List[UUID] = Field(default_factory=list)


class MeetingScheduleUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    duration_minutes: Optional[int] = Field(None, ge=15, le=480)
    timezone: Optional[str] = Field(None, max_length=50)
    meeting_platform: Optional[str] = Field(None, pattern=r'^(zoom|teams|meet|custom)$')
    meeting_link: Optional[str] = Field(None, max_length=500)
    participants: Optional[List[UUID]] = None
    status: Optional[str] = Field(None, pattern=r'^(scheduled|started|completed|cancelled)$')


class MeetingScheduleResponse(BaseModel):
    id: UUID
    organization_id: UUID
    project_id: Optional[UUID]
    title: str
    description: Optional[str]
    meeting_type: str
    scheduled_at: datetime
    duration_minutes: int
    timezone: str
    meeting_link: Optional[str]
    meeting_platform: str
    organizer_id: UUID
    participants: Optional[List[UUID]]
    status: str
    reminder_sent: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TaskAssignmentRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    assigned_to: List[UUID] = Field(..., min_items=1)
    priority: str = Field(default='medium', pattern=r'^(low|medium|high|urgent)$')
    due_date: Optional[datetime] = None
    project_id: Optional[UUID] = None
    board_id: Optional[UUID] = None
    column_id: Optional[UUID] = None


class TaskAssignmentResponse(BaseModel):
    id: UUID
    title: str
    description: Optional[str]
    assigned_to: List[UUID]
    priority: str
    due_date: Optional[datetime]
    status: str
    created_by: UUID
    created_at: datetime

    class Config:
        from_attributes = True


class RoleChangeRequest(BaseModel):
    user_id: UUID
    new_role: str = Field(..., pattern=r'^(viewer|member|admin)$')  # owner cannot be changed
    reason: Optional[str] = None


class DashboardPermissions(BaseModel):
    can_create_projects: bool
    can_schedule_meetings: bool
    can_invite_members: bool
    can_change_roles: bool
    can_view_all_projects: bool
    can_manage_organization: bool


class EnhancedOrganizationResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str]
    domain: Optional[str]
    allowed_domains: Optional[List[str]]
    contact_email: Optional[str]
    contact_phone: Optional[str]
    address_line1: Optional[str]
    address_line2: Optional[str]
    city: Optional[str]
    state: Optional[str]
    postal_code: Optional[str]
    country: Optional[str]
    organization_category: Optional[str]
    language: Optional[str]
    logo_url: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    # Enhanced fields
    settings: Optional[OrganizationSettingsResponse]
    user_role: str  # Current user's role in this organization
    permissions: DashboardPermissions
    member_count: int
    project_count: int

    class Config:
        from_attributes = True


class OrganizationListResponse(BaseModel):
    organizations: List[EnhancedOrganizationResponse]
    current_organization_id: Optional[UUID]
    total_count: int

    class Config:
        from_attributes = True
