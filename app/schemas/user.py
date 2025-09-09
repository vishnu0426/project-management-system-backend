"""
User schemas
"""
from pydantic import BaseModel, EmailStr, validator
from typing import Optional, List
from datetime import datetime
from uuid import UUID


class UserProfileUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    
    @validator('first_name', 'last_name')
    def validate_names(cls, v):
        if v is not None:
            if not v.strip():
                raise ValueError('Name cannot be empty')
            if len(v.strip()) < 2:
                raise ValueError('Name must be at least 2 characters long')
            return v.strip()
        return v


class UserProfile(BaseModel):
    id: UUID
    email: str
    first_name: str
    last_name: str
    avatar_url: Optional[str] = None
    email_verified: bool
    two_factor_enabled: bool
    last_login_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class UserOrganizationInfo(BaseModel):
    id: UUID
    name: str
    role: str

    class Config:
        from_attributes = True


class UserProfileWithRole(BaseModel):
    id: UUID
    email: str
    first_name: str
    last_name: str
    avatar_url: Optional[str] = None
    email_verified: bool
    two_factor_enabled: bool
    last_login_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    # Role and organization information
    role: Optional[str] = None
    organizations: List[UserOrganizationInfo] = []
    current_organization_id: Optional[UUID] = None

    class Config:
        from_attributes = True


class NotificationPreferences(BaseModel):
    email_notifications: bool = True
    push_notifications: bool = True
    task_assignments: bool = True
    task_updates: bool = True
    comments: bool = True
    mentions: bool = True
    project_updates: bool = True
    weekly_digest: bool = True


class NotificationPreferencesUpdate(BaseModel):
    email_notifications: Optional[bool] = None
    push_notifications: Optional[bool] = None
    task_assignments: Optional[bool] = None
    task_updates: Optional[bool] = None
    comments: Optional[bool] = None
    mentions: Optional[bool] = None
    project_updates: Optional[bool] = None
    weekly_digest: Optional[bool] = None
