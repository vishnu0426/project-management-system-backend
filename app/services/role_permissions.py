"""
Role-based permission service for task assignments and other features
"""
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.user import User
from app.models.organization import OrganizationMember


class RolePermissions:
    """Role-based permission system"""
    
    # Role hierarchy and permissions
    ROLE_HIERARCHY = {
        'viewer': 0,
        'member': 1,
        'admin': 2,
        'owner': 3
    }
    
    ROLE_PERMISSIONS = {
        'viewer': {
            'can_assign_tasks_to_self': True,
            'can_assign_tasks_to_others': False,
            'can_create_tasks': False,
            'can_edit_own_tasks': False,
            'can_edit_other_tasks': False,
            'can_delete_tasks': False,
            'can_manage_projects': False,
            'can_invite_members': False,
            'can_manage_members': False,
            'assignment_scope': 'self'
        },
        'member': {
            'can_assign_tasks_to_self': True,
            'can_assign_tasks_to_others': False,
            'can_create_tasks': True,
            'can_edit_own_tasks': True,
            'can_edit_other_tasks': False,
            'can_delete_tasks': False,
            'can_manage_projects': False,
            'can_invite_members': False,
            'can_manage_members': False,
            'assignment_scope': 'self'
        },
        'admin': {
            'can_assign_tasks_to_self': True,
            'can_assign_tasks_to_others': True,
            'can_create_tasks': True,
            'can_edit_own_tasks': True,
            'can_edit_other_tasks': True,
            'can_delete_tasks': True,
            'can_manage_projects': True,
            'can_invite_members': True,
            'can_manage_members': True,
            'assignment_scope': 'project'
        },
        'owner': {
            'can_assign_tasks_to_self': True,
            'can_assign_tasks_to_others': True,
            'can_create_tasks': True,
            'can_edit_own_tasks': True,
            'can_edit_other_tasks': True,
            'can_delete_tasks': True,
            'can_manage_projects': True,
            'can_invite_members': True,
            'can_manage_members': True,
            'assignment_scope': 'organization'
        }
    }

    @classmethod
    def get_role_permissions(cls, role: str) -> dict:
        """Get permissions for a specific role"""
        normalized_role = role.lower() if role else 'member'
        return cls.ROLE_PERMISSIONS.get(normalized_role, cls.ROLE_PERMISSIONS['member'])

    @classmethod
    def can_assign_task_to_user(cls, user_role: str, current_user_id: str, target_user_id: str) -> bool:
        """Check if user can assign tasks to other members"""
        permissions = cls.get_role_permissions(user_role)
        
        # Self-assignment is always allowed for all roles
        if current_user_id == target_user_id:
            return permissions['can_assign_tasks_to_self']
        
        # Check if user can assign to others
        return permissions['can_assign_tasks_to_others']

    @classmethod
    async def get_assignable_members(
        cls, 
        db: AsyncSession, 
        organization_id: str, 
        user_role: str, 
        current_user_id: str
    ) -> List[dict]:
        """Filter assignable members based on user role and permissions"""
        permissions = cls.get_role_permissions(user_role)
        
        # Get all organization members
        result = await db.execute(
            select(OrganizationMember, User)
            .join(User, OrganizationMember.user_id == User.id)
            .where(OrganizationMember.organization_id == organization_id)
        )
        members = result.all()
        
        assignable_members = []
        for org_member, user in members:
            # Check if current user can assign to this member
            if cls.can_assign_task_to_user(user_role, current_user_id, str(user.id)):
                assignable_members.append({
                    'id': str(user.id),
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'role': org_member.role,
                    'avatar_url': user.avatar_url
                })
        
        return assignable_members

    @classmethod
    def get_assignment_restriction_message(cls, user_role: str) -> str:
        """Get assignment restriction message for UI display"""
        permissions = cls.get_role_permissions(user_role)
        
        scope = permissions['assignment_scope']
        if scope == 'self':
            return f"{user_role.title()}s can only assign tasks to themselves"
        elif scope == 'project':
            return "Admins can assign tasks to project team members"
        elif scope == 'organization':
            return "Owners can assign tasks to any organization member"
        else:
            return "Task assignment not available for your role"

    @classmethod
    def can_receive_task_assignments(cls, user_role: str) -> bool:
        """Check if user can receive task assignments"""
        # All roles can receive task assignments, but with different restrictions
        return user_role.lower() in ['member', 'admin', 'owner']

    @classmethod
    def get_role_level(cls, role: str) -> int:
        """Get role hierarchy level"""
        return cls.ROLE_HIERARCHY.get(role.lower() if role else 'member', 0)

    @classmethod
    def has_minimum_role(cls, user_role: str, required_role: str) -> bool:
        """Check if user has higher or equal role than required"""
        return cls.get_role_level(user_role) >= cls.get_role_level(required_role)

    @classmethod
    async def validate_task_assignment(
        cls,
        db: AsyncSession,
        organization_id: str,
        current_user: User,
        target_user_ids: List[str]
    ) -> dict:
        """Validate task assignment permissions"""
        # Get current user's role in organization
        org_member_result = await db.execute(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == organization_id,
                OrganizationMember.user_id == current_user.id
            )
        )
        org_member = org_member_result.scalar_one_or_none()
        
        if not org_member:
            return {
                'valid': False,
                'error': 'User is not a member of this organization',
                'error_code': 'NOT_ORGANIZATION_MEMBER'
            }
        
        user_role = org_member.role
        permissions = cls.get_role_permissions(user_role)
        
        # Check each target user
        invalid_assignments = []
        for target_user_id in target_user_ids:
            if not cls.can_assign_task_to_user(user_role, str(current_user.id), target_user_id):
                invalid_assignments.append(target_user_id)
        
        if invalid_assignments:
            return {
                'valid': False,
                'error': cls.get_assignment_restriction_message(user_role),
                'error_code': 'INVALID_ASSIGNMENT',
                'invalid_users': invalid_assignments
            }
        
        return {'valid': True}

    @classmethod
    def can_create_tasks(cls, user_role: str) -> bool:
        """Check if user can create tasks"""
        permissions = cls.get_role_permissions(user_role)
        return permissions['can_create_tasks']

    @classmethod
    def can_edit_task(cls, user_role: str, is_task_creator: bool) -> bool:
        """Check if user can edit a task"""
        permissions = cls.get_role_permissions(user_role)
        
        if permissions['can_edit_other_tasks']:
            return True
        
        if permissions['can_edit_own_tasks'] and is_task_creator:
            return True
        
        return False

    @classmethod
    def can_delete_tasks(cls, user_role: str) -> bool:
        """Check if user can delete tasks"""
        permissions = cls.get_role_permissions(user_role)
        return permissions['can_delete_tasks']


# Create singleton instance
role_permissions = RolePermissions()
