"""
Enhanced Notification Service
Comprehensive notification system for all role interactions and changes
"""
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import selectinload

from app.models.user import User
from app.models.organization import Organization, OrganizationMember
from app.models.project import Project
from app.models.card import Card, CardAssignment
from app.models.organization_settings import MeetingSchedule, OrganizationSettings
from app.models.ai_automation import SmartNotification
from app.core.exceptions import ValidationError


class EnhancedNotificationService:
    """Service for managing comprehensive notifications"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def send_role_change_notification(
        self,
        user_id: str,
        organization_id: str,
        old_role: str,
        new_role: str,
        changed_by: str
    ):
        """Send notification when user role changes"""
        
        # Get changer details
        changer_result = await self.db.execute(
            select(User).where(User.id == changed_by)
        )
        changer = changer_result.scalar_one_or_none()
        
        # Get organization details
        org_result = await self.db.execute(
            select(Organization).where(Organization.id == organization_id)
        )
        org = org_result.scalar_one_or_none()
        
        if not changer or not org:
            return
        
        # Send notification to user whose role changed
        notification = SmartNotification(
            organization_id=organization_id,
            user_id=user_id,
            notification_type='role_change',
            title=f'Role Updated in {org.name}',
            message=f'Your role has been changed from {old_role} to {new_role} by {changer.first_name} {changer.last_name}',
            priority='high',
            context_data={
                'old_role': old_role,
                'new_role': new_role,
                'changed_by': changed_by,
                'organization_id': organization_id
            },
            ai_generated=False,
            delivery_method='in_app'
        )
        
        self.db.add(notification)
        
        # Notify organization owners/admins about role changes
        await self._notify_admins_about_role_change(
            organization_id, user_id, old_role, new_role, changed_by
        )
        
        await self.db.commit()
    
    async def send_task_completion_notification(
        self,
        card_id: str,
        completed_by: str,
        organization_id: str
    ):
        """Send notification when task is completed"""
        
        # Get card and project details
        card_result = await self.db.execute(
            select(Card, Project)
            .join(Project, Project.id == Card.project_id)
            .where(Card.id == card_id)
        )
        
        card_project = card_result.first()
        if not card_project:
            return
        
        card, project = card_project
        
        # Get user details
        user_result = await self.db.execute(
            select(User).where(User.id == completed_by)
        )
        user = user_result.scalar_one_or_none()
        
        if not user:
            return
        
        # Get all admins and owners in the organization
        admins_result = await self.db.execute(
            select(OrganizationMember.user_id)
            .where(
                and_(
                    OrganizationMember.organization_id == organization_id,
                    OrganizationMember.role.in_(['admin', 'owner']),
                    OrganizationMember.user_id != completed_by
                )
            )
        )
        
        admin_ids = [row[0] for row in admins_result.all()]
        
        # Send notifications to admins
        for admin_id in admin_ids:
            notification = SmartNotification(
                organization_id=organization_id,
                user_id=admin_id,
                notification_type='task_completed',
                title=f'Task Completed: {card.title}',
                message=f'{user.first_name} {user.last_name} completed the task "{card.title}" in project {project.name}',
                priority='low',
                context_data={
                    'card_id': card_id,
                    'card_title': card.title,
                    'project_id': str(project.id),
                    'project_name': project.name,
                    'completed_by': completed_by
                },
                ai_generated=False,
                delivery_method='in_app'
            )
            
            self.db.add(notification)
        
        await self.db.commit()
    
    async def send_project_update_notification(
        self,
        project_id: str,
        updated_by: str,
        update_type: str,  # created, updated, deleted
        changes: Optional[Dict[str, Any]] = None
    ):
        """Send notification when project is updated"""
        
        # Get project details
        project_result = await self.db.execute(
            select(Project).where(Project.id == project_id)
        )
        project = project_result.scalar_one_or_none()
        
        if not project:
            return
        
        # Get updater details
        user_result = await self.db.execute(
            select(User).where(User.id == updated_by)
        )
        user = user_result.scalar_one_or_none()
        
        if not user:
            return
        
        # Get organization members who should be notified
        members_result = await self.db.execute(
            select(OrganizationMember.user_id, OrganizationMember.role)
            .where(
                and_(
                    OrganizationMember.organization_id == project.organization_id,
                    OrganizationMember.user_id != updated_by
                )
            )
        )
        
        members = members_result.all()
        
        # Create notification message based on update type
        if update_type == 'created':
            title = f'New Project: {project.name}'
            message = f'{user.first_name} {user.last_name} created a new project: "{project.name}"'
        elif update_type == 'updated':
            title = f'Project Updated: {project.name}'
            message = f'{user.first_name} {user.last_name} updated the project: "{project.name}"'
        elif update_type == 'deleted':
            title = f'Project Deleted: {project.name}'
            message = f'{user.first_name} {user.last_name} deleted the project: "{project.name}"'
        else:
            return
        
        # Send notifications based on role
        for user_id, role in members:
            # Only notify admins and owners for project changes
            if role in ['admin', 'owner']:
                notification = SmartNotification(
                    organization_id=project.organization_id,
                    user_id=user_id,
                    notification_type='project_update',
                    title=title,
                    message=message,
                    priority='normal',
                    context_data={
                        'project_id': project_id,
                        'project_name': project.name,
                        'update_type': update_type,
                        'updated_by': updated_by,
                        'changes': changes
                    },
                    ai_generated=False,
                    delivery_method='in_app'
                )
                
                self.db.add(notification)
        
        await self.db.commit()

    async def send_project_completion_reminder(
        self,
        project_id: str,
    ) -> None:
        """Send a reminder to admins and owners when a project is fully completed.

        A project is considered fully completed when there are no remaining
        incomplete checklist items across any cards within the project. If
        sign‑off has already been requested on the project, this reminder will
        not be sent again. Duplicate reminders are avoided by checking for
        existing notifications of type ``project_completion`` for the same
        project and user.

        Parameters
        ----------
        project_id: str
            ID of the project to evaluate for completion.

        Notes
        -----
        This method performs the following steps:

        1. Queries the number of incomplete checklist items across all cards
           belonging to the specified project. If there are any incomplete
           items, the project is not yet complete and the method exits.
        2. Retrieves the project and checks whether a sign‑off request has
           already been made. If sign‑off has been requested, no reminder is
           sent.
        3. Retrieves all organization members with roles ``admin`` or
           ``owner`` and sends each a notification indicating that the
           project has been completed and is ready for review and sign‑off.
           Duplicate notifications are avoided by checking existing
           ``SmartNotification`` records for the same project and user.
        4. Commits the notifications to the database.
        """

        # Import here to avoid circular imports
        from sqlalchemy import select, func, and_
        from app.models.card import Card, ChecklistItem
        from app.models.column import Column
        from app.models.board import Board
        from app.models.project import Project
        from app.models.organization import OrganizationMember
        from app.models.ai_automation import SmartNotification

        # Determine if there are any incomplete checklist items in the project
        incomplete_result = await self.db.execute(
            select(func.count(ChecklistItem.id))
            .join(Card, ChecklistItem.card_id == Card.id)
            .join(Column, Card.column_id == Column.id)
            .join(Board, Column.board_id == Board.id)
            .where(
                Board.project_id == project_id,
                ChecklistItem.completed == False  # noqa: E712 – explicit comparison is intentional
            )
        )
        incomplete_count = incomplete_result.scalar_one_or_none() or 0
        # If there are incomplete items, do not send a reminder
        if incomplete_count > 0:
            return

        # Retrieve the project
        project_result = await self.db.execute(
            select(Project).where(Project.id == project_id)
        )
        project = project_result.scalar_one_or_none()
        if not project:
            return

        # Do not send a reminder if sign‑off has already been requested
        if project.sign_off_requested:
            return

        organization_id = project.organization_id

        # Fetch all admin and owner members of the organization
        members_result = await self.db.execute(
            select(OrganizationMember.user_id)
            .where(
                and_(
                    OrganizationMember.organization_id == organization_id,
                    OrganizationMember.role.in_(['admin', 'owner'])
                )
            )
        )
        member_ids = [row[0] for row in members_result.fetchall()]

        if not member_ids:
            return

        # For each admin/owner, ensure we only send one reminder per project
        for user_id in member_ids:
            # Fetch existing completion notifications for this user
            existing_result = await self.db.execute(
                select(SmartNotification)
                .where(
                    and_(
                        SmartNotification.organization_id == organization_id,
                        SmartNotification.user_id == user_id,
                        SmartNotification.notification_type == 'project_completion'
                    )
                )
            )
            existing_notifications = existing_result.scalars().all()
            # Check if a notification for this specific project already exists
            skip = False
            for n in existing_notifications:
                try:
                    ctx = n.context_data or {}
                    if ctx.get('project_id') == project_id:
                        skip = True
                        break
                except Exception:
                    # If context_data is not a dict or missing, ignore
                    continue
            if skip:
                continue  # Duplicate exists; skip sending

            notification = SmartNotification(
                organization_id=organization_id,
                user_id=user_id,
                notification_type='project_completion',
                title=f'Project Completed: {project.name}',
                message=(
                    f'All tasks and checklist items for project "{project.name}" '
                    'are completed. Please review and request sign‑off.'
                ),
                priority='high',
                context_data={
                    'project_id': project_id,
                    'project_name': project.name
                },
                ai_generated=False,
                delivery_method='in_app'
            )
            self.db.add(notification)

        await self.db.commit()
    
    async def send_meeting_reminder_notifications(self):
        """Send reminders for upcoming meetings (background task)"""
        
        # Get meetings starting in the next 15 minutes
        now = datetime.utcnow()
        reminder_time = now + timedelta(minutes=15)
        
        meetings_result = await self.db.execute(
            select(MeetingSchedule)
            .where(
                and_(
                    MeetingSchedule.scheduled_at <= reminder_time,
                    MeetingSchedule.scheduled_at > now,
                    MeetingSchedule.status == 'scheduled',
                    MeetingSchedule.reminder_sent == False
                )
            )
        )
        
        meetings = meetings_result.scalars().all()
        
        for meeting in meetings:
            if meeting.participants:
                # Send reminder to all participants
                for participant_id in meeting.participants:
                    notification = SmartNotification(
                        organization_id=meeting.organization_id,
                        user_id=participant_id,
                        notification_type='meeting_reminder',
                        title=f'Meeting Reminder: {meeting.title}',
                        message=f'Your meeting "{meeting.title}" starts in 15 minutes',
                        priority='high',
                        context_data={
                            'meeting_id': str(meeting.id),
                            'meeting_title': meeting.title,
                            'scheduled_at': meeting.scheduled_at.isoformat(),
                            'meeting_link': meeting.meeting_link
                        },
                        ai_generated=False,
                        delivery_method='in_app'
                    )
                    
                    self.db.add(notification)
                
                # Mark reminder as sent
                meeting.reminder_sent = True
        
        await self.db.commit()
        print(f"✅ Sent meeting reminders for {len(meetings)} meetings")
    
    async def send_overdue_task_notifications(self):
        """Send notifications for overdue tasks (background task)"""
        
        now = datetime.utcnow()
        
        # Get overdue tasks
        overdue_tasks_result = await self.db.execute(
            select(Card, CardAssignment, Project)
            .join(CardAssignment, CardAssignment.card_id == Card.id)
            .join(Project, Project.id == Card.project_id)
            .where(
                and_(
                    Card.due_date < now,
                    Card.status != 'completed',
                    CardAssignment.status == 'accepted'
                )
            )
        )
        
        overdue_tasks = overdue_tasks_result.all()
        
        for card, assignment, project in overdue_tasks:
            # Notify assigned user
            notification = SmartNotification(
                organization_id=project.organization_id,
                user_id=assignment.user_id,
                notification_type='task_overdue',
                title=f'Overdue Task: {card.title}',
                message=f'Your task "{card.title}" was due on {card.due_date.strftime("%Y-%m-%d")}',
                priority='urgent',
                context_data={
                    'card_id': str(card.id),
                    'card_title': card.title,
                    'due_date': card.due_date.isoformat(),
                    'project_name': project.name
                },
                ai_generated=False,
                delivery_method='in_app'
            )
            
            self.db.add(notification)
            
            # Also notify admins about overdue tasks
            await self._notify_admins_about_overdue_task(
                project.organization_id, card, assignment.user_id
            )
        
        await self.db.commit()
        print(f"✅ Sent overdue task notifications for {len(overdue_tasks)} tasks")
    
    async def get_user_notifications(
        self,
        user_id: str,
        organization_id: str,
        unread_only: bool = False,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get notifications for user"""
        
        query = select(SmartNotification).where(
            and_(
                SmartNotification.user_id == user_id,
                SmartNotification.organization_id == organization_id
            )
        )
        
        if unread_only:
            query = query.where(SmartNotification.read_at.is_(None))
        
        query = query.order_by(SmartNotification.created_at.desc()).limit(limit)
        
        result = await self.db.execute(query)
        notifications = result.scalars().all()
        
        return [
            {
                'id': str(n.id),
                'title': n.title,
                'message': n.message,
                'type': n.notification_type,
                'priority': n.priority,
                'context_data': n.context_data,
                'read': n.read_at is not None,
                'created_at': n.created_at.isoformat(),
                'read_at': n.read_at.isoformat() if n.read_at else None
            }
            for n in notifications
        ]
    
    async def mark_notification_read(self, notification_id: str, user_id: str) -> bool:
        """Mark notification as read"""
        
        result = await self.db.execute(
            select(SmartNotification)
            .where(
                and_(
                    SmartNotification.id == notification_id,
                    SmartNotification.user_id == user_id
                )
            )
        )
        
        notification = result.scalar_one_or_none()
        if not notification:
            return False
        
        notification.read_at = datetime.utcnow()
        await self.db.commit()
        return True
    
    async def get_notification_stats(
        self,
        user_id: str,
        organization_id: str
    ) -> Dict[str, int]:
        """Get notification statistics for user"""
        
        stats_result = await self.db.execute(
            select(
                func.count(SmartNotification.id).label('total'),
                func.count(SmartNotification.id).filter(SmartNotification.read_at.is_(None)).label('unread'),
                func.count(SmartNotification.id).filter(SmartNotification.priority == 'urgent').label('urgent'),
                func.count(SmartNotification.id).filter(SmartNotification.priority == 'high').label('high')
            )
            .where(
                and_(
                    SmartNotification.user_id == user_id,
                    SmartNotification.organization_id == organization_id
                )
            )
        )
        
        stats = stats_result.first()
        
        return {
            'total': stats.total if stats else 0,
            'unread': stats.unread if stats else 0,
            'urgent': stats.urgent if stats else 0,
            'high': stats.high if stats else 0
        }
    
    async def _notify_admins_about_role_change(
        self,
        organization_id: str,
        user_id: str,
        old_role: str,
        new_role: str,
        changed_by: str
    ):
        """Notify admins about role changes"""
        
        # Get organization owners
        owners_result = await self.db.execute(
            select(OrganizationMember.user_id)
            .where(
                and_(
                    OrganizationMember.organization_id == organization_id,
                    OrganizationMember.role == 'owner',
                    OrganizationMember.user_id != changed_by
                )
            )
        )
        
        owner_ids = [row[0] for row in owners_result.all()]
        
        # Get user details
        user_result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = user_result.scalar_one_or_none()
        
        if not user:
            return
        
        # Send notifications to owners
        for owner_id in owner_ids:
            notification = SmartNotification(
                organization_id=organization_id,
                user_id=owner_id,
                notification_type='admin_role_change',
                title=f'Role Change: {user.first_name} {user.last_name}',
                message=f'User role changed from {old_role} to {new_role}',
                priority='normal',
                context_data={
                    'affected_user_id': user_id,
                    'old_role': old_role,
                    'new_role': new_role,
                    'changed_by': changed_by
                },
                ai_generated=False,
                delivery_method='in_app'
            )
            
            self.db.add(notification)
    
    async def _notify_admins_about_overdue_task(
        self,
        organization_id: str,
        card: Card,
        assigned_user_id: str
    ):
        """Notify admins about overdue tasks"""
        
        # Get admins and owners
        admins_result = await self.db.execute(
            select(OrganizationMember.user_id)
            .where(
                and_(
                    OrganizationMember.organization_id == organization_id,
                    OrganizationMember.role.in_(['admin', 'owner'])
                )
            )
        )
        
        admin_ids = [row[0] for row in admins_result.all()]
        
        # Get assigned user details
        user_result = await self.db.execute(
            select(User).where(User.id == assigned_user_id)
        )
        user = user_result.scalar_one_or_none()
        
        if not user:
            return
        
        # Send notifications to admins
        for admin_id in admin_ids:
            notification = SmartNotification(
                organization_id=organization_id,
                user_id=admin_id,
                notification_type='admin_overdue_task',
                title=f'Overdue Task Alert: {card.title}',
                message=f'Task "{card.title}" assigned to {user.first_name} {user.last_name} is overdue',
                priority='high',
                context_data={
                    'card_id': str(card.id),
                    'card_title': card.title,
                    'assigned_user_id': assigned_user_id,
                    'due_date': card.due_date.isoformat()
                },
                ai_generated=False,
                delivery_method='in_app'
            )
            
            self.db.add(notification)
