"""
Checklist schemas
"""
from pydantic import BaseModel, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID


class ChecklistItemCreate(BaseModel):
    text: str
    position: int
    ai_generated: bool = False
    confidence: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None
    
    @validator('text')
    def validate_text(cls, v):
        if not v.strip():
            raise ValueError('Checklist item text cannot be empty')
        return v.strip()
    
    @validator('position')
    def validate_position(cls, v):
        if v < 0:
            raise ValueError('Position must be non-negative')
        return v
    
    @validator('confidence')
    def validate_confidence(cls, v):
        if v is not None and (v < 0 or v > 100):
            raise ValueError('Confidence must be between 0 and 100')
        return v


class ChecklistItemUpdate(BaseModel):
    text: Optional[str] = None
    completed: Optional[bool] = None
    is_completed: Optional[bool] = None  # Support both field names
    position: Optional[int] = None

    @validator('text')
    def validate_text(cls, v):
        if v is not None and not v.strip():
            raise ValueError('Checklist item text cannot be empty')
        return v.strip() if v else v

    @validator('position')
    def validate_position(cls, v):
        if v is not None and v < 0:
            raise ValueError('Position must be non-negative')
        return v


class ChecklistItemResponse(BaseModel):
    id: UUID
    card_id: UUID
    text: str
    completed: bool
    position: int
    ai_generated: bool
    confidence: Optional[int] = None
    ai_metadata: Optional[Dict[str, Any]] = None
    created_by: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ChecklistItemOut(BaseModel):
    """Standard checklist item output schema matching frontend expectations"""
    id: str
    checklist_id: Optional[str] = None  # For compatibility
    content: str  # Maps to 'text' field
    is_completed: bool  # Maps to 'completed' field
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True

    @classmethod
    def from_checklist_item(cls, item):
        """Convert from ChecklistItem model"""
        return cls(
            id=str(item.id),
            checklist_id=str(item.card_id),  # Use card_id as checklist_id
            content=item.text,
            is_completed=item.completed,
            completed_at=item.completed_at
        )


class ChecklistBulkCreate(BaseModel):
    items: List[ChecklistItemCreate]
    
    @validator('items')
    def validate_items(cls, v):
        if not v:
            raise ValueError('At least one checklist item is required')
        if len(v) > 20:
            raise ValueError('Maximum 20 checklist items allowed')
        return v


class ChecklistBulkUpdate(BaseModel):
    items: List[ChecklistItemUpdate]


class AIChecklistRequest(BaseModel):
    title: str
    description: Optional[str] = None
    priority: str = 'medium'
    project_type: Optional[str] = None
    
    @validator('title')
    def validate_title(cls, v):
        if not v.strip():
            raise ValueError('Title cannot be empty')
        return v.strip()
    
    @validator('priority')
    def validate_priority(cls, v):
        if v not in ['low', 'medium', 'high', 'urgent']:
            raise ValueError('Priority must be low, medium, high, or urgent')
        return v


class AIChecklistResponse(BaseModel):
    success: bool
    items: List[Dict[str, Any]]
    metadata: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class ChecklistSuggestionsResponse(BaseModel):
    suggestions: List[str]
    task_type: str


class ChecklistProgressResponse(BaseModel):
    total_items: int
    completed_items: int
    progress_percentage: float
    ai_generated_count: int


class ChecklistValidationRequest(BaseModel):
    assigned_to: List[str]  # List of user IDs
    
    @validator('assigned_to')
    def validate_assigned_to(cls, v):
        if not v:
            raise ValueError('At least one user must be assigned')
        return v


class ChecklistValidationResponse(BaseModel):
    valid: bool
    error: Optional[str] = None
    error_code: Optional[str] = None
    invalid_users: Optional[List[str]] = None
    assignable_members: Optional[List[Dict[str, Any]]] = None


class RolePermissionsResponse(BaseModel):
    can_assign_tasks_to_self: bool
    can_assign_tasks_to_others: bool
    can_create_tasks: bool
    can_edit_own_tasks: bool
    can_edit_other_tasks: bool
    can_delete_tasks: bool
    assignment_scope: str
    restriction_message: str


class AssignableMembersResponse(BaseModel):
    members: List[Dict[str, Any]]
    total_count: int
    user_role: str
    assignment_scope: str
