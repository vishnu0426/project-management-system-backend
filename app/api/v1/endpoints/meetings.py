"""
Meeting management endpoints for AI Task Management Modal
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, or_
from sqlalchemy.orm import selectinload
from pydantic import BaseModel, Field
from uuid import UUID
import uuid
from datetime import datetime, timedelta

from app.core.database import get_db
from app.core.deps import get_current_active_user
from app.core.exceptions import ValidationError, ResourceNotFoundError, InsufficientPermissionsError
from app.models.user import User
from app.models.organization import OrganizationMember
from app.models.project import Project
from app.models.organization_settings import MeetingSchedule
from app.models.ai_automation import SmartNotification
from app.services.organization_service import OrganizationService
from app.middleware.role_based_access import require_permission
from app.services.enhanced_role_permissions import Permission

router = APIRouter()

# Pydantic models for meeting endpoints
class MeetingCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    project_id: str
    meeting_type: str = Field(pattern="^(standup|planning|review|retrospective|custom)$")
    start_time: datetime
    duration: int = Field(ge=15, le=480)  # 15 minutes to 8 hours
    attendees: List[str] = []
    agenda: Optional[List[str]] = []
    is_recurring: bool = False
    recurrence_pattern: Optional[Dict[str, Any]] = None

class MeetingUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    start_time: Optional[datetime] = None
    duration: Optional[int] = None
    attendees: Optional[List[str]] = None
    agenda: Optional[List[str]] = None
    status: Optional[str] = None

class InstantMeetingRequest(BaseModel):
    project_id: str
    meeting_type: str
    title: str
    attendees: List[str] = []
    duration: int = Field(default=30, ge=15, le=120)

class CalendarIntegrationRequest(BaseModel):
    provider: str = Field(pattern="^(google|microsoft|outlook)$")
    auth_code: str
    project_id: Optional[str] = None

class MeetingResponse(BaseModel):
    id: str
    title: str
    description: Optional[str]
    project_id: str
    meeting_type: str
    start_time: datetime
    duration: int
    attendees: List[Dict[str, Any]]
    agenda: List[str]
    status: str
    meeting_url: Optional[str]
    is_recurring: bool
    created_at: datetime
    created_by: str

# In-memory storage for demo (replace with database models)
meetings_db = {}
calendar_integrations_db = {}

@router.post("/create", response_model=MeetingResponse)
async def create_meeting(
    meeting_data: MeetingCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new meeting"""
    try:
        # Verify project access
        project_result = await db.execute(
            select(Project).where(Project.id == meeting_data.project_id)
        )
        project = project_result.scalar_one_or_none()
        if not project:
            raise ResourceNotFoundError("Project not found")

        # Check organization membership
        org_member_result = await db.execute(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == project.organization_id,
                OrganizationMember.user_id == current_user.id
            )
        )
        org_member = org_member_result.scalar_one_or_none()
        if not org_member:
            raise InsufficientPermissionsError("Access denied to project")

        # Generate meeting ID and URL
        meeting_id = str(uuid.uuid4())
        meeting_url = await generate_meeting_url(meeting_data.meeting_type)

        # Create meeting record
        meeting = {
            "id": meeting_id,
            "title": meeting_data.title,
            "description": meeting_data.description,
            "project_id": meeting_data.project_id,
            "meeting_type": meeting_data.meeting_type,
            "start_time": meeting_data.start_time,
            "duration": meeting_data.duration,
            "attendees": await get_attendee_details(meeting_data.attendees, db),
            "agenda": meeting_data.agenda or [],
            "status": "scheduled",
            "meeting_url": meeting_url,
            "is_recurring": meeting_data.is_recurring,
            "recurrence_pattern": meeting_data.recurrence_pattern,
            "created_at": datetime.utcnow(),
            "created_by": str(current_user.id),
            "organization_id": project.organization_id
        }

        meetings_db[meeting_id] = meeting

        # Schedule notifications
        background_tasks.add_task(
            send_meeting_notifications,
            meeting_id,
            meeting_data.attendees,
            "created"
        )

        # Create calendar events if integrations exist
        background_tasks.add_task(
            create_calendar_events,
            meeting_id,
            project.organization_id
        )

        return MeetingResponse(**meeting)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create meeting: {str(e)}")

@router.post("/instant", response_model=MeetingResponse)
async def create_instant_meeting(
    meeting_data: InstantMeetingRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create and start an instant meeting"""
    try:
        # Verify project access
        project_result = await db.execute(
            select(Project).where(Project.id == meeting_data.project_id)
        )
        project = project_result.scalar_one_or_none()
        if not project:
            raise ResourceNotFoundError("Project not found")

        # Generate instant meeting
        meeting_id = str(uuid.uuid4())
        meeting_url = await generate_instant_meeting_url()

        meeting = {
            "id": meeting_id,
            "title": meeting_data.title,
            "description": f"Instant {meeting_data.meeting_type} meeting",
            "project_id": meeting_data.project_id,
            "meeting_type": meeting_data.meeting_type,
            "start_time": datetime.utcnow(),
            "duration": meeting_data.duration,
            "attendees": await get_attendee_details(meeting_data.attendees, db),
            "agenda": [],
            "status": "in_progress",
            "meeting_url": meeting_url,
            "is_recurring": False,
            "created_at": datetime.utcnow(),
            "created_by": str(current_user.id),
            "organization_id": project.organization_id
        }

        meetings_db[meeting_id] = meeting

        # Send instant notifications
        await send_instant_meeting_notifications(meeting_url, meeting_data.attendees)

        return MeetingResponse(**meeting)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create instant meeting: {str(e)}")

@router.get("/project/{project_id}")
async def get_project_meetings(
    project_id: str,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get meetings for a project"""
    try:
        # Verify project access
        project_result = await db.execute(
            select(Project).where(Project.id == project_id)
        )
        project = project_result.scalar_one_or_none()
        if not project:
            raise ResourceNotFoundError("Project not found")

        # Filter meetings
        project_meetings = [
            meeting for meeting in meetings_db.values()
            if meeting["project_id"] == project_id
        ]

        if status:
            project_meetings = [
                meeting for meeting in project_meetings
                if meeting["status"] == status
            ]

        return {
            "success": True,
            "data": project_meetings,
            "message": f"Retrieved {len(project_meetings)} meetings"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get meetings: {str(e)}")

@router.put("/{meeting_id}")
async def update_meeting(
    meeting_id: str,
    meeting_data: MeetingUpdate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a meeting"""
    try:
        if meeting_id not in meetings_db:
            raise ResourceNotFoundError("Meeting not found")

        meeting = meetings_db[meeting_id]

        # Check permissions
        if meeting["created_by"] != str(current_user.id):
            # Check if user is admin/owner of organization
            org_member_result = await db.execute(
                select(OrganizationMember).where(
                    OrganizationMember.organization_id == meeting["organization_id"],
                    OrganizationMember.user_id == current_user.id,
                    OrganizationMember.role.in_(["owner", "admin"])
                )
            )
            org_member = org_member_result.scalar_one_or_none()
            if not org_member:
                raise InsufficientPermissionsError("Insufficient permissions to update meeting")

        # Update meeting
        update_data = meeting_data.dict(exclude_unset=True)
        meeting.update(update_data)
        meetings_db[meeting_id] = meeting

        # Notify attendees of changes
        background_tasks.add_task(
            send_meeting_notifications,
            meeting_id,
            [attendee["id"] for attendee in meeting["attendees"]],
            "updated"
        )

        return {
            "success": True,
            "data": meeting,
            "message": "Meeting updated successfully"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update meeting: {str(e)}")

@router.delete("/{meeting_id}")
async def delete_meeting(
    meeting_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a meeting"""
    try:
        if meeting_id not in meetings_db:
            raise ResourceNotFoundError("Meeting not found")

        meeting = meetings_db[meeting_id]

        # Check permissions
        if meeting["created_by"] != str(current_user.id):
            org_member_result = await db.execute(
                select(OrganizationMember).where(
                    OrganizationMember.organization_id == meeting["organization_id"],
                    OrganizationMember.user_id == current_user.id,
                    OrganizationMember.role.in_(["owner", "admin"])
                )
            )
            org_member = org_member_result.scalar_one_or_none()
            if not org_member:
                raise InsufficientPermissionsError("Insufficient permissions to delete meeting")

        # Delete meeting
        del meetings_db[meeting_id]

        return {
            "success": True,
            "message": "Meeting deleted successfully"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete meeting: {str(e)}")

@router.post("/calendar/integrate")
async def integrate_calendar(
    integration_data: CalendarIntegrationRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Integrate with external calendar provider"""
    try:
        # This would typically involve OAuth flow with the calendar provider
        integration_id = str(uuid.uuid4())
        
        integration = {
            "id": integration_id,
            "user_id": str(current_user.id),
            "provider": integration_data.provider,
            "status": "connected",
            "created_at": datetime.utcnow(),
            "access_token": "encrypted_token_here",  # Would be encrypted
            "refresh_token": "encrypted_refresh_token_here"
        }

        calendar_integrations_db[integration_id] = integration

        return {
            "success": True,
            "data": integration,
            "message": f"Successfully integrated with {integration_data.provider}"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to integrate calendar: {str(e)}")

# Helper functions
async def generate_meeting_url(meeting_type: str) -> str:
    """Generate meeting URL based on type"""
    # This would integrate with actual video conferencing APIs
    base_urls = {
        "standup": "https://meet.google.com/",
        "planning": "https://zoom.us/j/",
        "review": "https://teams.microsoft.com/",
        "retrospective": "https://meet.google.com/",
        "custom": "https://meet.google.com/"
    }
    
    base_url = base_urls.get(meeting_type, "https://meet.google.com/")
    room_id = str(uuid.uuid4())[:10]
    return f"{base_url}{room_id}"

async def generate_instant_meeting_url() -> str:
    """Generate instant meeting URL"""
    room_id = str(uuid.uuid4())[:10]
    return f"https://meet.google.com/{room_id}"

async def get_attendee_details(attendee_ids: List[str], db: AsyncSession) -> List[Dict[str, Any]]:
    """Get attendee details from user IDs"""
    if not attendee_ids:
        return []
    
    users_result = await db.execute(
        select(User).where(User.id.in_(attendee_ids))
    )
    users = users_result.scalars().all()
    
    return [
        {
            "id": str(user.id),
            "name": f"{user.first_name} {user.last_name}",
            "email": user.email,
            "avatar": user.avatar_url
        }
        for user in users
    ]

async def send_meeting_notifications(meeting_id: str, attendee_ids: List[str], action: str):
    """Send meeting notifications to attendees"""
    # This would integrate with notification service
    print(f"Sending {action} notifications for meeting {meeting_id} to {len(attendee_ids)} attendees")

async def send_instant_meeting_notifications(meeting_url: str, attendee_ids: List[str]):
    """Send instant meeting notifications"""
    # This would send immediate notifications
    print(f"Sending instant meeting notifications to {len(attendee_ids)} attendees: {meeting_url}")

async def create_calendar_events(meeting_id: str, organization_id: str):
    """Create calendar events for integrated calendars"""
    # This would create events in external calendars
    print(f"Creating calendar events for meeting {meeting_id} in organization {organization_id}")


# Enhanced Meeting Endpoints with Database Integration

@router.post("/enhanced/schedule")
@require_permission(Permission.SCHEDULE_MEETING)
async def schedule_enhanced_meeting(
    meeting_data: dict,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Schedule meeting with database storage and notifications"""

    # Get organization context
    org_service = OrganizationService(db)
    organization_id = await org_service.get_current_organization(str(current_user.id))
    if not organization_id:
        raise HTTPException(status_code=400, detail="No organization context")

    # Create meeting in database
    meeting = MeetingSchedule(
        organization_id=organization_id,
        project_id=meeting_data.get('project_id'),
        title=meeting_data['title'],
        description=meeting_data.get('description'),
        meeting_type=meeting_data.get('meeting_type', 'team'),
        scheduled_at=datetime.fromisoformat(meeting_data['scheduled_at']),
        duration_minutes=meeting_data.get('duration_minutes', 60),
        timezone=meeting_data.get('timezone', 'UTC'),
        meeting_platform=meeting_data.get('meeting_platform', 'zoom'),
        meeting_link=meeting_data.get('meeting_link'),
        organizer_id=current_user.id,
        participants=meeting_data.get('participants', [])
    )

    db.add(meeting)
    await db.commit()
    await db.refresh(meeting)

    # Send notifications
    if meeting.participants:
        background_tasks.add_task(
            send_enhanced_meeting_notifications,
            str(meeting.id),
            meeting.participants,
            str(current_user.id),
            organization_id,
            'scheduled',
            db
        )

    return {
        'success': True,
        'meeting_id': str(meeting.id),
        'message': f'Meeting "{meeting.title}" scheduled successfully',
        'scheduled_at': meeting.scheduled_at.isoformat(),
        'participants_notified': len(meeting.participants) if meeting.participants else 0
    }


@router.post("/enhanced/{meeting_id}/join")
async def join_enhanced_meeting(
    meeting_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Join meeting with enhanced functionality"""

    result = await db.execute(
        select(MeetingSchedule).where(MeetingSchedule.id == meeting_id)
    )
    meeting = result.scalar_one_or_none()

    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    # Check access
    user_id_str = str(current_user.id)
    if (meeting.organizer_id != current_user.id and
        (not meeting.participants or user_id_str not in meeting.participants)):
        raise HTTPException(status_code=403, detail="Access denied to this meeting")

    # Check timing (allow joining 15 minutes early)
    now = datetime.utcnow()
    if meeting.scheduled_at > now + timedelta(minutes=15):
        raise HTTPException(
            status_code=400,
            detail=f"Meeting starts at {meeting.scheduled_at.isoformat()}. Too early to join."
        )

    # Mark as started if organizer joins
    if meeting.organizer_id == current_user.id and meeting.status == 'scheduled':
        meeting.status = 'started'
        await db.commit()

    # Generate meeting link if not exists
    if not meeting.meeting_link:
        meeting.meeting_link = f"https://{meeting.meeting_platform}.example.com/join/{meeting_id}"
        await db.commit()

    return {
        'meeting_id': str(meeting.id),
        'title': meeting.title,
        'meeting_link': meeting.meeting_link,
        'platform': meeting.meeting_platform,
        'status': meeting.status,
        'join_now': True,
        'message': 'Click the link to join the meeting'
    }


@router.get("/enhanced/calendar/{organization_id}")
async def get_enhanced_meeting_calendar(
    organization_id: str,
    month: Optional[int] = None,
    year: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get meeting calendar with enhanced features"""

    # Verify organization access
    member_result = await db.execute(
        select(OrganizationMember)
        .where(
            and_(
                OrganizationMember.user_id == current_user.id,
                OrganizationMember.organization_id == organization_id
            )
        )
    )

    if not member_result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Access denied to organization")

    # Set date range
    now = datetime.utcnow()
    if month and year:
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = datetime(year, month + 1, 1) - timedelta(days=1)
    else:
        start_date = datetime(now.year, now.month, 1)
        if now.month == 12:
            end_date = datetime(now.year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = datetime(now.year, now.month + 1, 1) - timedelta(days=1)

    # Get meetings
    result = await db.execute(
        select(MeetingSchedule)
        .where(
            and_(
                MeetingSchedule.organization_id == organization_id,
                MeetingSchedule.scheduled_at >= start_date,
                MeetingSchedule.scheduled_at <= end_date,
                or_(
                    MeetingSchedule.organizer_id == current_user.id,
                    MeetingSchedule.participants.contains([str(current_user.id)])
                )
            )
        )
        .order_by(MeetingSchedule.scheduled_at.asc())
    )

    meetings = result.scalars().all()

    # Group by date
    calendar_data = {}
    for meeting in meetings:
        date_key = meeting.scheduled_at.date().isoformat()
        if date_key not in calendar_data:
            calendar_data[date_key] = []

        # Check if meeting can be joined now
        can_join_now = (
            meeting.status in ['scheduled', 'started'] and
            meeting.scheduled_at <= now + timedelta(minutes=15)
        )

        calendar_data[date_key].append({
            'id': str(meeting.id),
            'title': meeting.title,
            'time': meeting.scheduled_at.strftime('%H:%M'),
            'duration': meeting.duration_minutes,
            'status': meeting.status,
            'is_organizer': meeting.organizer_id == current_user.id,
            'meeting_type': meeting.meeting_type,
            'can_join_now': can_join_now,
            'meeting_link': meeting.meeting_link
        })

    return {
        'calendar_month': f"{start_date.year}-{start_date.month:02d}",
        'meetings_by_date': calendar_data,
        'total_meetings': len(meetings)
    }


async def send_enhanced_meeting_notifications(
    meeting_id: str,
    participant_ids: List[str],
    organizer_id: str,
    organization_id: str,
    action: str,
    db: AsyncSession
):
    """Enhanced meeting notifications with database storage"""
    try:
        # Get meeting and organizer details
        meeting_result = await db.execute(
            select(MeetingSchedule).where(MeetingSchedule.id == meeting_id)
        )
        meeting = meeting_result.scalar_one_or_none()

        organizer_result = await db.execute(
            select(User).where(User.id == organizer_id)
        )
        organizer = organizer_result.scalar_one_or_none()

        if not meeting or not organizer:
            return

        # Create notifications
        for participant_id in participant_ids:
            if participant_id != organizer_id:
                notification = SmartNotification(
                    organization_id=organization_id,
                    user_id=participant_id,
                    notification_type='meeting_notification',
                    title=f'Meeting {action.title()}: {meeting.title}',
                    message=f'{organizer.first_name} {organizer.last_name} {action} a meeting: "{meeting.title}" on {meeting.scheduled_at.strftime("%Y-%m-%d at %H:%M")}',
                    priority='normal',
                    context_data={
                        'meeting_id': meeting_id,
                        'meeting_title': meeting.title,
                        'scheduled_at': meeting.scheduled_at.isoformat(),
                        'action': action,
                        'can_join': action == 'scheduled'
                    },
                    ai_generated=False,
                    delivery_method='in_app'
                )

                db.add(notification)

        await db.commit()
        print(f"✅ Sent enhanced meeting notifications for {meeting_id}")

    except Exception as e:
        print(f"❌ Failed to send enhanced meeting notifications: {str(e)}")
