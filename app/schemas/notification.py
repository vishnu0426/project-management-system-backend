"""
Notification schemas
"""
from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from uuid import UUID


class NotificationBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    message: str = Field(..., min_length=1)
    type: str = Field(..., min_length=1, max_length=50)
    priority: str = Field(default="normal", pattern="^(low|normal|high|urgent)$")
    action_url: Optional[str] = Field(None, max_length=500)
    notification_metadata: Optional[Dict[str, Any]] = None


class NotificationCreate(NotificationBase):
    user_id: UUID
    organization_id: Optional[UUID] = None


class NotificationUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    message: Optional[str] = Field(None, min_length=1)
    priority: Optional[str] = Field(None, pattern="^(low|normal|high|urgent)$")
    action_url: Optional[str] = Field(None, max_length=500)
    notification_metadata: Optional[Dict[str, Any]] = None
    read: Optional[bool] = None


class NotificationResponse(NotificationBase):
    id: UUID
    user_id: UUID
    organization_id: Optional[UUID]
    read: bool
    created_at: datetime
    read_at: Optional[datetime]
    expires_at: Optional[datetime]

    class Config:
        from_attributes = True


class NotificationPreferenceBase(BaseModel):
    notification_type: str = Field(..., min_length=1, max_length=50)
    email_enabled: bool = True
    push_enabled: bool = True
    in_app_enabled: bool = True


class NotificationPreferenceCreate(NotificationPreferenceBase):
    user_id: UUID


class NotificationPreferenceUpdate(BaseModel):
    email_enabled: Optional[bool] = None
    push_enabled: Optional[bool] = None
    in_app_enabled: Optional[bool] = None


class NotificationPreferenceResponse(NotificationPreferenceBase):
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class NotificationStats(BaseModel):
    total_notifications: int
    unread_notifications: int
    read_notifications: int


class BulkNotificationCreate(BaseModel):
    user_ids: list[UUID]
    title: str = Field(..., min_length=1, max_length=255)
    message: str = Field(..., min_length=1)
    type: str = Field(..., min_length=1, max_length=50)
    priority: str = Field(default="normal", pattern="^(low|normal|high|urgent)$")
    organization_id: Optional[UUID] = None
    action_url: Optional[str] = Field(None, max_length=500)
    notification_metadata: Optional[Dict[str, Any]] = None
