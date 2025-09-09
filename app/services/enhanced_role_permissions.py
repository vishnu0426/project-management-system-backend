"""
Enhanced Role-Based Access Control Service
Comprehensive role permissions for owner/admin/member with specific operation restrictions
"""
from typing import Dict, List, Optional, Any
from enum import Enum
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.models.user import User
from app.models.organization import OrganizationMember
from app.models.organization_settings import OrganizationSettings
from app.models.project import Project
from app.models.card import Card, CardAssignment
from app.core.exceptions import InsufficientPermissionsError


class Permission(Enum):
    """Detailed permission enumeration"""
    # Organization Management
    CREATE_ORGANIZATION = "create_organization"
    MANAGE_ORGANIZATION = "manage_organization"
    DELETE_ORGANIZATION = "delete_organization"
    UPDATE_ORG_SETTINGS = "update_org_settings"
    
    # Project Management
    CREATE_PROJECT = "create_project"
    VIEW_ALL_PROJECTS = "view_all_projects"
    VIEW_ASSIGNED_PROJECTS = "view_assigned_projects"
    UPDATE_PROJECT = "update_project"
    DELETE_PROJECT = "delete_project"
    
    # Member Management
    INVITE_ADMIN = "invite_admin"
    INVITE_MEMBER = "invite_member"
    PROMOTE_TO_ADMIN = "promote_to_admin"
    PROMOTE_TO_MEMBER = "promote_to_member"
    DEMOTE_ADMIN = "demote_admin"
    DEMOTE_MEMBER = "demote_member"
    REMOVE_MEMBER = "remove_member"
    
    # Task Management
    CREATE_TASK = "create_task"
    ASSIGN_TASK = "assign_task"
    VIEW_ALL_TASKS = "view_all_tasks"
    VIEW_ASSIGNED_TASKS = "view_assigned_tasks"
    UPDATE_TASK = "update_task"
    DELETE_TASK = "delete_task"
    ACCEPT_TASK = "accept_task"
    
    # Meeting Management
    SCHEDULE_MEETING = "schedule_meeting"
    SCHEDULE_TEAM_MEETING = "schedule_team_meeting"
    SCHEDULE_INDIVIDUAL_MEETING = "schedule_individual_meeting"
    JOIN_MEETING = "join_meeting"
    CANCEL_MEETING = "cancel_meeting"
    
    # Kanban Board Operations
    CREATE_BOARD = "create_board"
    UPDATE_BOARD = "update_board"
    DELETE_BOARD = "delete_board"
    CREATE_COLUMN = "create_column"
    UPDATE_COLUMN = "update_column"
    DELETE_COLUMN = "delete_column"
    CREATE_CARD = "create_card"
    UPDATE_OWN_CARD = "update_own_card"
    UPDATE_ANY_CARD = "update_any_card"
    DELETE_OWN_CARD = "delete_own_card"
    DELETE_ANY_CARD = "delete_any_card"
    MOVE_CARD = "move_card"
    
    # Notification Management
    SEND_NOTIFICATION = "send_notification"
    VIEW_ALL_NOTIFICATIONS = "view_all_notifications"
    MANAGE_NOTIFICATION_SETTINGS = "manage_notification_settings"


class EnhancedRolePermissions:
    """Enhanced role-based permission system"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        
        # Define role permissions
        self.role_permissions = {
            'owner': {
                # Organization Management
                Permission.CREATE_ORGANIZATION,
                Permission.MANAGE_ORGANIZATION,
                Permission.DELETE_ORGANIZATION,
                Permission.UPDATE_ORG_SETTINGS,
                
                # Project Management
                Permission.CREATE_PROJECT,
                Permission.VIEW_ALL_PROJECTS,
                Permission.UPDATE_PROJECT,
                Permission.DELETE_PROJECT,
                
                # Member Management
                Permission.INVITE_ADMIN,
                Permission.INVITE_MEMBER,
                Permission.PROMOTE_TO_ADMIN,
                Permission.PROMOTE_TO_MEMBER,
                Permission.DEMOTE_ADMIN,
                Permission.DEMOTE_MEMBER,
                Permission.REMOVE_MEMBER,
                
                # Task Management
                Permission.CREATE_TASK,
                Permission.ASSIGN_TASK,
                Permission.VIEW_ALL_TASKS,
                Permission.UPDATE_TASK,
                Permission.DELETE_TASK,
                
                # Meeting Management
                Permission.SCHEDULE_MEETING,
                Permission.SCHEDULE_TEAM_MEETING,
                Permission.SCHEDULE_INDIVIDUAL_MEETING,
                Permission.JOIN_MEETING,
                Permission.CANCEL_MEETING,
                
                # Kanban Board Operations
                Permission.CREATE_BOARD,
                Permission.UPDATE_BOARD,
                Permission.DELETE_BOARD,
                Permission.CREATE_COLUMN,
                Permission.UPDATE_COLUMN,
                Permission.DELETE_COLUMN,
                Permission.CREATE_CARD,
                Permission.UPDATE_OWN_CARD,
                Permission.UPDATE_ANY_CARD,
                Permission.DELETE_OWN_CARD,
                Permission.DELETE_ANY_CARD,
                Permission.MOVE_CARD,
                
                # Notification Management
                Permission.SEND_NOTIFICATION,
                Permission.VIEW_ALL_NOTIFICATIONS,
                Permission.MANAGE_NOTIFICATION_SETTINGS,
            },
            
            'admin': {
                # Project Management (if allowed by org settings)
                Permission.VIEW_ALL_PROJECTS,
                Permission.UPDATE_PROJECT,
                
                # Member Management (limited)
                Permission.INVITE_MEMBER,
                Permission.PROMOTE_TO_MEMBER,
                Permission.DEMOTE_MEMBER,
                
                # Task Management
                Permission.CREATE_TASK,
                Permission.ASSIGN_TASK,
                Permission.VIEW_ALL_TASKS,
                Permission.UPDATE_TASK,
                Permission.DELETE_TASK,
                
                # Meeting Management (if allowed by org settings)
                Permission.JOIN_MEETING,
                
                # Kanban Board Operations
                Permission.CREATE_BOARD,
                Permission.UPDATE_BOARD,
                Permission.CREATE_COLUMN,
                Permission.UPDATE_COLUMN,
                Permission.CREATE_CARD,
                Permission.UPDATE_OWN_CARD,
                Permission.UPDATE_ANY_CARD,
                Permission.DELETE_OWN_CARD,
                Permission.DELETE_ANY_CARD,
                Permission.MOVE_CARD,
                
                # Notification Management
                Permission.SEND_NOTIFICATION,
                Permission.VIEW_ALL_NOTIFICATIONS,
            },
            
            'member': {
                # Project Management
                Permission.VIEW_ASSIGNED_PROJECTS,

                # Task Management
                Permission.VIEW_ASSIGNED_TASKS,
                Permission.ACCEPT_TASK,
                Permission.UPDATE_OWN_CARD,  # Only own assigned cards

                # Meeting Management
                Permission.JOIN_MEETING,

                # Kanban Board Operations (limited to own content)
                Permission.CREATE_BOARD,  # Can create boards
                Permission.UPDATE_BOARD,  # Only own boards (checked in _check_resource_permission)
                Permission.DELETE_BOARD,  # Only own boards (checked in _check_resource_permission)
                Permission.CREATE_CARD,  # Can create cards
                Permission.UPDATE_OWN_CARD,  # Only own cards
                Permission.DELETE_OWN_CARD,  # Only own cards
                Permission.MOVE_CARD,  # Only own cards
            },
            
            'viewer': {
                # Very limited permissions
                Permission.VIEW_ASSIGNED_PROJECTS,
                Permission.VIEW_ASSIGNED_TASKS,
                Permission.JOIN_MEETING,
            }
        }

    async def check_permission(
        self, 
        user_id: str, 
        organization_id: str, 
        permission: Permission,
        resource_id: Optional[str] = None
    ) -> bool:
        """Check if user has specific permission in organization"""
        try:
            # Get user's role in organization
            role = await self.get_user_role(user_id, organization_id)
            if not role:
                return False
            
            # Get base permissions for role
            base_permissions = self.role_permissions.get(role, set())
            
            # Check if permission is in base permissions
            if permission not in base_permissions:
                return False
            
            # Apply organization settings for conditional permissions
            if permission in [Permission.CREATE_PROJECT, Permission.SCHEDULE_MEETING, Permission.SCHEDULE_TEAM_MEETING]:
                return await self._check_conditional_permission(organization_id, role, permission)
            
            # Apply resource-specific checks
            if resource_id:
                return await self._check_resource_permission(user_id, organization_id, permission, resource_id)
            
            return True
            
        except Exception:
            return False

    async def get_user_role(self, user_id: str, organization_id: str) -> Optional[str]:
        """Get user's role in organization"""
        result = await self.db.execute(
            select(OrganizationMember.role)
            .where(
                and_(
                    OrganizationMember.user_id == user_id,
                    OrganizationMember.organization_id == organization_id
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_user_permissions(self, user_id: str, organization_id: str) -> List[str]:
        """Get all permissions for user in organization"""
        role = await self.get_user_role(user_id, organization_id)
        if not role:
            return []
        
        base_permissions = self.role_permissions.get(role, set())
        permissions = []
        
        for permission in base_permissions:
            if await self.check_permission(user_id, organization_id, permission):
                permissions.append(permission.value)
        
        return permissions

    async def require_permission(
        self, 
        user_id: str, 
        organization_id: str, 
        permission: Permission,
        resource_id: Optional[str] = None
    ):
        """Require permission or raise exception"""
        if not await self.check_permission(user_id, organization_id, permission, resource_id):
            raise InsufficientPermissionsError(f"Permission denied: {permission.value}")

    async def can_manage_user_role(
        self, 
        manager_id: str, 
        target_user_id: str, 
        organization_id: str,
        new_role: str
    ) -> bool:
        """Check if manager can change target user's role"""
        manager_role = await self.get_user_role(manager_id, organization_id)
        target_role = await self.get_user_role(target_user_id, organization_id)
        
        if not manager_role or not target_role:
            return False
        
        # Owner can manage all roles except other owners
        if manager_role == 'owner':
            return target_role != 'owner' and new_role != 'owner'
        
        # Admin can only promote/demote members
        if manager_role == 'admin':
            return target_role == 'member' and new_role == 'member'
        
        return False

    async def get_accessible_projects(self, user_id: str, organization_id: str) -> List[str]:
        """Get list of project IDs user can access"""
        role = await self.get_user_role(user_id, organization_id)
        
        if role in ['owner', 'admin']:
            # Can access all projects in organization
            result = await self.db.execute(
                select(Project.id)
                .where(Project.organization_id == organization_id)
            )
            return [str(project_id) for project_id in result.scalars().all()]
        
        elif role in ['member', 'viewer']:
            # Can only access assigned projects
            result = await self.db.execute(
                select(Project.id)
                .join(CardAssignment, CardAssignment.card_id == Card.id)
                .join(Card, Card.project_id == Project.id)
                .where(
                    and_(
                        Project.organization_id == organization_id,
                        CardAssignment.user_id == user_id
                    )
                )
                .distinct()
            )
            return [str(project_id) for project_id in result.scalars().all()]
        
        return []

    async def _check_conditional_permission(
        self, 
        organization_id: str, 
        role: str, 
        permission: Permission
    ) -> bool:
        """Check permissions that depend on organization settings"""
        settings_result = await self.db.execute(
            select(OrganizationSettings)
            .where(OrganizationSettings.organization_id == organization_id)
        )
        
        settings = settings_result.scalar_one_or_none()
        if not settings:
            # Default permissions if no settings
            return role in ['owner', 'admin']
        
        if permission == Permission.CREATE_PROJECT:
            if role == 'admin':
                return settings.allow_admin_create_projects
            elif role == 'member':
                return settings.allow_member_create_projects
        
        elif permission in [Permission.SCHEDULE_MEETING, Permission.SCHEDULE_TEAM_MEETING]:
            if role == 'admin':
                return settings.allow_admin_schedule_meetings
            elif role == 'member':
                return settings.allow_member_schedule_meetings
        
        return True

    async def _check_resource_permission(
        self,
        user_id: str,
        organization_id: str,
        permission: Permission,
        resource_id: str
    ) -> bool:
        """Check resource-specific permissions"""
        from app.models.card import Card
        from app.models.board import Board

        # For card operations, check ownership for members
        if permission in [Permission.UPDATE_OWN_CARD, Permission.DELETE_OWN_CARD, Permission.UPDATE_ANY_CARD, Permission.DELETE_ANY_CARD]:
            user_role = await self.get_user_role(user_id, organization_id)

            # Owners and admins can modify any card
            if user_role in ['owner', 'admin']:
                return True

            # Members can only modify cards they created
            if user_role == 'member':
                result = await self.db.execute(
                    select(Card).where(Card.id == resource_id)
                )
                card = result.scalar_one_or_none()
                return card is not None and str(card.created_by) == user_id

            return False

        # For board operations, check ownership for members
        if permission in [Permission.UPDATE_BOARD, Permission.DELETE_BOARD]:
            user_role = await self.get_user_role(user_id, organization_id)

            # Owners and admins can modify any board
            if user_role in ['owner', 'admin']:
                return True

            # Members can only modify boards they created
            if user_role == 'member':
                result = await self.db.execute(
                    select(Board).where(Board.id == resource_id)
                )
                board = result.scalar_one_or_none()
                return board is not None and str(board.created_by) == user_id

            return False

        return True

    async def can_view_resource(
        self,
        user_id: str,
        organization_id: str,
        resource_type: str,
        resource_id: str
    ) -> bool:
        """Check if user can view a resource (more permissive than edit)"""
        user_role = await self.get_user_role(user_id, organization_id)

        if not user_role:
            return False

        # All roles can view content within their organization
        # This implements the requirement that members can view all allocated content
        return True

    async def can_modify_resource(
        self,
        user_id: str,
        organization_id: str,
        resource_type: str,
        resource_id: str
    ) -> bool:
        """Check if user can modify a resource (ownership-based for members)"""
        user_role = await self.get_user_role(user_id, organization_id)

        if not user_role:
            return False

        # Owners and admins can modify any resource
        if user_role in ['owner', 'admin']:
            return True

        # Members can only modify resources they created
        if user_role == 'member':
            if resource_type == 'card':
                from app.models.card import Card
                result = await self.db.execute(
                    select(Card).where(Card.id == resource_id)
                )
                card = result.scalar_one_or_none()
                return card is not None and str(card.created_by) == user_id

            elif resource_type == 'board':
                from app.models.board import Board
                result = await self.db.execute(
                    select(Board).where(Board.id == resource_id)
                )
                board = result.scalar_one_or_none()
                return board is not None and str(board.created_by) == user_id

        # Viewers cannot modify anything
        return False
