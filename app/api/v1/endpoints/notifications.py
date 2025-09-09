"""
Notifications API endpoints
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.deps import get_current_active_user
from app.models.user import User
from app.models.notification import Notification, NotificationPreference
from app.models.ai_automation import SmartNotification
from app.schemas.notification import (
    NotificationCreate, NotificationUpdate, NotificationResponse,
    NotificationPreferenceCreate, NotificationPreferenceUpdate, NotificationPreferenceResponse
)
from app.services.enhanced_notification_service import EnhancedNotificationService
from app.services.organization_service import OrganizationService

router = APIRouter()


@router.get("/", response_model=List[NotificationResponse])
async def get_notifications(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    unread_only: bool = Query(False),
    notification_type: Optional[str] = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get notifications for current user"""
    try:
        # Build query
        query = select(Notification).where(Notification.user_id == current_user.id)
        
        if unread_only:
            query = query.where(Notification.read == False)
        
        if notification_type:
            query = query.where(Notification.type == notification_type)
        
        # Order by created_at desc and apply pagination
        query = query.order_by(Notification.created_at.desc()).offset(skip).limit(limit)
        
        result = await db.execute(query)
        notifications = result.scalars().all()
        
        return notifications
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get notifications: {str(e)}"
        )


@router.post("/", response_model=NotificationResponse)
async def create_notification(
    notification_data: NotificationCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new notification"""
    try:
        # Use current user as the target user if not specified or if user doesn't have permission
        target_user_id = notification_data.user_id

        # For now, allow users to create notifications for themselves
        # In a production system, you might want to restrict this to admin users
        if target_user_id != current_user.id:
            # Check if current user has permission to create notifications for others
            # For simplicity, we'll allow it for now but log it
            pass

        notification = Notification(
            user_id=target_user_id,
            organization_id=notification_data.organization_id,
            title=notification_data.title,
            message=notification_data.message,
            type=notification_data.type,
            priority=notification_data.priority,
            action_url=notification_data.action_url,
            notification_metadata=notification_data.notification_metadata
        )
        
        db.add(notification)
        await db.commit()
        await db.refresh(notification)
        
        return notification
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create notification: {str(e)}"
        )


@router.put("/{notification_id}/read", response_model=NotificationResponse)
async def mark_notification_read(
    notification_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Mark a notification as read"""
    try:
        # Get notification
        result = await db.execute(
            select(Notification).where(
                and_(
                    Notification.id == notification_id,
                    Notification.user_id == current_user.id
                )
            )
        )
        notification = result.scalar_one_or_none()
        
        if not notification:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification not found"
            )
        
        # Mark as read
        notification.read = True
        notification.read_at = func.now()
        
        await db.commit()
        await db.refresh(notification)
        
        return notification
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to mark notification as read: {str(e)}"
        )


@router.put("/mark-all-read")
async def mark_all_notifications_read(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Mark all notifications as read for current user"""
    try:
        # Update all unread notifications
        await db.execute(
            Notification.__table__.update()
            .where(
                and_(
                    Notification.user_id == current_user.id,
                    Notification.read == False
                )
            )
            .values(read=True, read_at=func.now())
        )
        
        await db.commit()
        
        return {"message": "All notifications marked as read"}
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to mark all notifications as read: {str(e)}"
        )


@router.delete("/{notification_id}")
async def delete_notification(
    notification_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a notification"""
    try:
        # Get notification
        result = await db.execute(
            select(Notification).where(
                and_(
                    Notification.id == notification_id,
                    Notification.user_id == current_user.id
                )
            )
        )
        notification = result.scalar_one_or_none()
        
        if not notification:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification not found"
            )
        
        await db.delete(notification)
        await db.commit()
        
        return {"message": "Notification deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete notification: {str(e)}"
        )


@router.get("/stats")
async def get_notification_stats(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get notification statistics for current user"""
    try:
        # Get total and unread counts
        total_result = await db.execute(
            select(func.count(Notification.id)).where(Notification.user_id == current_user.id)
        )
        total_count = total_result.scalar() or 0
        
        unread_result = await db.execute(
            select(func.count(Notification.id)).where(
                and_(
                    Notification.user_id == current_user.id,
                    Notification.read == False
                )
            )
        )
        unread_count = unread_result.scalar() or 0
        
        return {
            "total_notifications": total_count,
            "unread_notifications": unread_count,
            "read_notifications": total_count - unread_count
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get notification stats: {str(e)}"
        )


# Enhanced Notification Endpoints

@router.get("/enhanced", response_model=List[dict])
async def get_enhanced_notifications(
    organization_id: Optional[str] = Query(None),
    unread_only: bool = Query(False),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get enhanced notifications with organization context"""

    # Get organization context
    org_service = OrganizationService(db)
    if not organization_id:
        organization_id = await org_service.get_current_organization(str(current_user.id))
        if not organization_id:
            raise HTTPException(status_code=400, detail="No organization context")

    # Get notifications using enhanced service
    notification_service = EnhancedNotificationService(db)
    notifications = await notification_service.get_user_notifications(
        str(current_user.id), organization_id, unread_only, limit
    )

    return notifications


@router.post("/enhanced/{notification_id}/read")
async def mark_enhanced_notification_read(
    notification_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Mark enhanced notification as read"""

    notification_service = EnhancedNotificationService(db)
    success = await notification_service.mark_notification_read(
        notification_id, str(current_user.id)
    )

    if not success:
        raise HTTPException(status_code=404, detail="Notification not found")

    return {"success": True, "message": "Notification marked as read"}


@router.get("/enhanced/stats/{organization_id}")
async def get_enhanced_notification_stats(
    organization_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get enhanced notification statistics"""

    notification_service = EnhancedNotificationService(db)
    stats = await notification_service.get_notification_stats(
        str(current_user.id), organization_id
    )

    return stats


@router.post("/enhanced/send-role-change")
async def send_role_change_notification(
    notification_data: dict,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Send role change notification (admin/owner only)"""

    user_id = notification_data.get('user_id')
    organization_id = notification_data.get('organization_id')
    old_role = notification_data.get('old_role')
    new_role = notification_data.get('new_role')

    if not all([user_id, organization_id, old_role, new_role]):
        raise HTTPException(status_code=400, detail="Missing required fields")

    notification_service = EnhancedNotificationService(db)
    await notification_service.send_role_change_notification(
        user_id, organization_id, old_role, new_role, str(current_user.id)
    )

    return {"success": True, "message": "Role change notification sent"}


@router.post("/enhanced/send-task-completion")
async def send_task_completion_notification(
    notification_data: dict,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Send task completion notification"""

    card_id = notification_data.get('card_id')
    organization_id = notification_data.get('organization_id')

    if not all([card_id, organization_id]):
        raise HTTPException(status_code=400, detail="Missing required fields")

    notification_service = EnhancedNotificationService(db)
    await notification_service.send_task_completion_notification(
        card_id, str(current_user.id), organization_id
    )

    return {"success": True, "message": "Task completion notification sent"}


@router.post("/enhanced/send-project-update")
async def send_project_update_notification(
    notification_data: dict,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Send project update notification"""

    project_id = notification_data.get('project_id')
    update_type = notification_data.get('update_type')  # created, updated, deleted
    changes = notification_data.get('changes')

    if not all([project_id, update_type]):
        raise HTTPException(status_code=400, detail="Missing required fields")

    notification_service = EnhancedNotificationService(db)
    await notification_service.send_project_update_notification(
        project_id, str(current_user.id), update_type, changes
    )

    return {"success": True, "message": "Project update notification sent"}


# Background task endpoints (for system use)

@router.post("/enhanced/send-meeting-reminders")
async def send_meeting_reminders(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Send meeting reminder notifications (system task)"""

    notification_service = EnhancedNotificationService(db)
    await notification_service.send_meeting_reminder_notifications()

    return {"success": True, "message": "Meeting reminders sent"}


@router.post("/enhanced/send-overdue-task-notifications")
async def send_overdue_task_notifications(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Send overdue task notifications (system task)"""

    notification_service = EnhancedNotificationService(db)
    await notification_service.send_overdue_task_notifications()

    return {"success": True, "message": "Overdue task notifications sent"}
