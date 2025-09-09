"""
Project schemas
"""
from pydantic import BaseModel, validator
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from uuid import UUID
import html


class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    status: str = "active"
    priority: str = "medium"
    start_date: Optional[date] = None
    due_date: Optional[date] = None
    
    @validator('name')
    def validate_name(cls, v):
        if not v.strip():
            raise ValueError('Project name cannot be empty')
        if len(v.strip()) < 2:
            raise ValueError('Project name must be at least 2 characters long')
        if len(v.strip()) > 255:
            raise ValueError('Project name cannot exceed 255 characters')
        # Sanitize HTML to prevent XSS
        sanitized = html.escape(v.strip())
        return sanitized

    @validator('description')
    def validate_description(cls, v):
        if v and len(v) > 2000:
            raise ValueError('Description cannot exceed 2000 characters')
        # Sanitize HTML to prevent XSS
        if v:
            return html.escape(v)
        return v
    
    @validator('status')
    def validate_status(cls, v):
        if v not in ['active', 'completed', 'on_hold', 'cancelled']:
            raise ValueError('Status must be active, completed, on_hold, or cancelled')
        return v
    
    @validator('priority')
    def validate_priority(cls, v):
        if v not in ['low', 'medium', 'high', 'urgent']:
            raise ValueError('Priority must be low, medium, high, or urgent')
        return v


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    start_date: Optional[date] = None
    due_date: Optional[date] = None
    
    @validator('name')
    def validate_name(cls, v):
        if v is not None:
            if not v.strip():
                raise ValueError('Project name cannot be empty')
            if len(v.strip()) < 2:
                raise ValueError('Project name must be at least 2 characters long')
            return v.strip()
        return v
    
    @validator('status')
    def validate_status(cls, v):
        if v is not None and v not in ['active', 'completed', 'on_hold', 'cancelled']:
            raise ValueError('Status must be active, completed, on_hold, or cancelled')
        return v
    
    @validator('priority')
    def validate_priority(cls, v):
        if v is not None and v not in ['low', 'medium', 'high', 'urgent']:
            raise ValueError('Priority must be low, medium, high, or urgent')
        return v


class ProjectResponse(BaseModel):
    id: UUID
    organization_id: UUID
    name: str
    description: Optional[str] = None
    status: str
    priority: str
    start_date: Optional[date] = None
    due_date: Optional[date] = None
    created_by: UUID
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# Enhanced Project Creation Schemas
class ProjectConfiguration(BaseModel):
    budget: Optional[float] = None
    duration: Optional[int] = None  # in weeks
    team_size: Optional[int] = None
    priority: str = "medium"
    methodology: str = "agile"
    resources: Optional[Dict[str, int]] = None  # e.g., {"frontend": 2, "backend": 2}
    tools: Optional[Dict[str, bool]] = None  # e.g., {"projectManagement": true}
    features: Optional[Dict[str, bool]] = None  # e.g., {"realTimeCollaboration": false}

class ProjectOverview(BaseModel):
    title: str
    description: str
    objectives: Optional[List[str]] = None
    deliverables: Optional[List[str]] = None
    kpis: Optional[List[Dict[str, str]]] = None  # e.g., [{"name": "User Satisfaction", "target": "95%"}]
    timeline: Optional[Dict[str, Any]] = None
    stakeholders: Optional[List[str]] = None
    risk_assessment: Optional[str] = None
    success_criteria: Optional[str] = None

class ProjectTechStack(BaseModel):
    frontend: Optional[List[str]] = None
    backend: Optional[List[str]] = None
    database: Optional[List[str]] = None
    cloud: Optional[List[str]] = None
    tools: Optional[List[str]] = None

class ProjectWorkflowPhase(BaseModel):
    id: str
    name: str
    duration: int  # in weeks
    tasks: List[Dict[str, Any]]

class ProjectWorkflow(BaseModel):
    phases: List[ProjectWorkflowPhase]

class ProjectTask(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    priority: str = "medium"
    status: str = "pending"
    due_date: Optional[date] = None
    assignee: Optional[str] = None
    category: Optional[str] = None
    dependencies: Optional[List[str]] = None
    subtasks: Optional[List[Dict[str, Any]]] = None
    estimated_hours: Optional[int] = None
    actual_hours: Optional[int] = None
    tags: Optional[List[str]] = None
    notes: Optional[str] = None

class EnhancedProjectCreate(BaseModel):
    # Basic project info
    name: str
    description: Optional[str] = None
    status: str = "active"
    priority: str = "medium"
    start_date: Optional[date] = None
    due_date: Optional[date] = None

    # Enhanced project data
    configuration: Optional[ProjectConfiguration] = None
    overview: Optional[ProjectOverview] = None
    tech_stack: Optional[ProjectTechStack] = None
    workflow: Optional[ProjectWorkflow] = None
    tasks: Optional[List[ProjectTask]] = None

    # Notification and launch settings
    notifications: Optional[Dict[str, bool]] = None
    launch_options: Optional[Dict[str, bool]] = None
    finalized_at: Optional[datetime] = None

    @validator('name')
    def validate_name(cls, v):
        if not v.strip():
            raise ValueError('Project name cannot be empty')
        if len(v.strip()) < 2:
            raise ValueError('Project name must be at least 2 characters long')
        return v.strip()

    @validator('status')
    def validate_status(cls, v):
        if v not in ['active', 'completed', 'on_hold', 'cancelled']:
            raise ValueError('Status must be active, completed, on_hold, or cancelled')
        return v

    @validator('priority')
    def validate_priority(cls, v):
        if v not in ['low', 'medium', 'high', 'urgent']:
            raise ValueError('Priority must be low, medium, high, or urgent')
        return v

class EnhancedProjectResponse(BaseModel):
    id: UUID
    organization_id: UUID
    name: str
    description: Optional[str] = None
    status: str
    priority: str
    start_date: Optional[date] = None
    due_date: Optional[date] = None
    created_by: UUID
    created_at: datetime
    updated_at: datetime

    # Enhanced project data
    configuration: Optional[Dict[str, Any]] = None
    overview: Optional[Dict[str, Any]] = None
    tech_stack: Optional[Dict[str, Any]] = None
    workflow: Optional[Dict[str, Any]] = None
    tasks: Optional[List[Dict[str, Any]]] = None
    notifications: Optional[Dict[str, bool]] = None
    launch_options: Optional[Dict[str, bool]] = None
    finalized_at: Optional[datetime] = None

    # Sign-off and Data Protection Fields
    sign_off_requested: bool = False
    sign_off_requested_at: Optional[datetime] = None
    sign_off_requested_by: Optional[UUID] = None
    sign_off_approved: bool = False
    sign_off_approved_at: Optional[datetime] = None
    sign_off_approved_by: Optional[UUID] = None
    sign_off_notes: Optional[str] = None
    data_protected: bool = False
    protection_reason: Optional[str] = None
    archived_at: Optional[datetime] = None
    archived_by: Optional[UUID] = None

    class Config:
        from_attributes = True


# Project Sign-off Schemas
class ProjectSignOffRequest(BaseModel):
    """Schema for requesting project sign-off"""
    notes: Optional[str] = None
    reason: Optional[str] = None

class ProjectSignOffApproval(BaseModel):
    """Schema for approving project sign-off"""
    approved: bool
    notes: Optional[str] = None
    unprotect_data: bool = False  # Whether to remove data protection after approval

class ProjectSignOffStatus(BaseModel):
    """Schema for project sign-off status"""
    project_id: UUID
    project_name: str
    sign_off_requested: bool
    sign_off_requested_at: Optional[datetime] = None
    sign_off_requested_by: Optional[UUID] = None
    requester_name: Optional[str] = None
    sign_off_approved: bool
    sign_off_approved_at: Optional[datetime] = None
    sign_off_approved_by: Optional[UUID] = None
    approver_name: Optional[str] = None
    sign_off_notes: Optional[str] = None
    data_protected: bool
    protection_reason: Optional[str] = None
    can_approve: bool = False  # Whether current user can approve

    class Config:
        from_attributes = True

class ProjectDataProtection(BaseModel):
    """Schema for project data protection settings"""
    data_protected: bool
    protection_reason: Optional[str] = None

class ProjectArchive(BaseModel):
    """Schema for archiving projects"""
    archive_reason: Optional[str] = None
    preserve_data: bool = True


class BoardCreate(BaseModel):
    """
    Schema used when creating a new board.  In addition to the board
    details, a project_id must be supplied when the board is created
    via the flat `/boards` endpoint.  If you are using the nested
    `/projects/{project_id}/boards` endpoint, the `project_id` field is
    ignored.
    """

    name: str
    project_id: Optional[str] = None
    description: Optional[str] = None

    @validator('name')
    def validate_name(cls, v):
        if not v.strip():
            raise ValueError('Board name cannot be empty')
        if len(v.strip()) < 2:
            raise ValueError('Board name must be at least 2 characters long')
        return v.strip()

    @validator('project_id')
    def validate_project_id(cls, v):
        # Allow project_id to be optional when using nested endpoint
        if v is not None and not str(v).strip():
            raise ValueError('project_id cannot be empty if provided')
        return v


class BoardUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    
    @validator('name')
    def validate_name(cls, v):
        if v is not None:
            if not v.strip():
                raise ValueError('Board name cannot be empty')
            if len(v.strip()) < 2:
                raise ValueError('Board name must be at least 2 characters long')
            return v.strip()
        return v


class BoardResponse(BaseModel):
    id: UUID
    project_id: UUID
    name: str
    description: Optional[str] = None
    created_by: UUID
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ColumnCreate(BaseModel):
    name: str
    position: int
    color: Optional[str] = None
    
    @validator('name')
    def validate_name(cls, v):
        if not v.strip():
            raise ValueError('Column name cannot be empty')
        return v.strip()
    
    @validator('position')
    def validate_position(cls, v):
        if v < 0:
            raise ValueError('Position must be non-negative')
        return v


class ColumnUpdate(BaseModel):
    name: Optional[str] = None
    position: Optional[int] = None
    color: Optional[str] = None
    
    @validator('name')
    def validate_name(cls, v):
        if v is not None and not v.strip():
            raise ValueError('Column name cannot be empty')
        return v.strip() if v else v
    
    @validator('position')
    def validate_position(cls, v):
        if v is not None and v < 0:
            raise ValueError('Position must be non-negative')
        return v


class ColumnOrderUpdate(BaseModel):
    column_orders: List[dict]  # [{"id": "col_id", "position": 0}, ...]


class ColumnResponse(BaseModel):
    id: UUID
    board_id: UUID
    name: str
    position: int
    color: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
