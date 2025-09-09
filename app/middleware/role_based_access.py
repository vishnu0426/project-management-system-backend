"""
Role-Based Access Control Middleware
Enhanced middleware for role-based access control with detailed permissions
"""
from typing import Callable, Optional
from functools import wraps
from fastapi import HTTPException, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_active_user
from app.models.user import User
from app.services.enhanced_role_permissions import EnhancedRolePermissions, Permission
from app.services.organization_service import OrganizationService


def require_permission(permission: Permission, resource_param: Optional[str] = None):
    """Decorator to require specific permission for endpoint access"""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract dependencies from kwargs
            current_user = None
            db = None
            organization_id = None
            resource_id = None
            
            for key, value in kwargs.items():
                if isinstance(value, User):
                    current_user = value
                elif hasattr(value, 'execute'):  # AsyncSession
                    db = value
                elif key == 'organization_id':
                    organization_id = value
                elif resource_param and key == resource_param:
                    resource_id = value
            
            if not current_user or not db:
                raise HTTPException(status_code=401, detail="Authentication required")
            
            # Get current organization if not provided
            if not organization_id:
                org_service = OrganizationService(db)
                organization_id = await org_service.get_current_organization(str(current_user.id))
                
                if not organization_id:
                    raise HTTPException(status_code=400, detail="No organization context")
            
            # Check permission
            permissions = EnhancedRolePermissions(db)
            await permissions.require_permission(
                str(current_user.id), 
                str(organization_id), 
                permission,
                str(resource_id) if resource_id else None
            )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def require_role(required_roles: list):
    """Decorator to require specific roles for endpoint access"""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract dependencies from kwargs
            current_user = None
            db = None
            organization_id = None
            
            for key, value in kwargs.items():
                if isinstance(value, User):
                    current_user = value
                elif hasattr(value, 'execute'):  # AsyncSession
                    db = value
                elif key == 'organization_id':
                    organization_id = value
            
            if not current_user or not db:
                raise HTTPException(status_code=401, detail="Authentication required")
            
            # Get current organization if not provided
            if not organization_id:
                org_service = OrganizationService(db)
                organization_id = await org_service.get_current_organization(str(current_user.id))
                
                if not organization_id:
                    raise HTTPException(status_code=400, detail="No organization context")
            
            # Check role
            permissions = EnhancedRolePermissions(db)
            user_role = await permissions.get_user_role(str(current_user.id), str(organization_id))
            
            if user_role not in required_roles:
                raise HTTPException(
                    status_code=403, 
                    detail=f"Required roles: {required_roles}, current role: {user_role}"
                )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


class RoleBasedAccessMiddleware:
    """Middleware class for role-based access control"""
    
    def __init__(self):
        self.permissions = None
    
    async def check_organization_access(
        self, 
        user_id: str, 
        organization_id: str, 
        db: AsyncSession
    ) -> bool:
        """Check if user has access to organization"""
        if not self.permissions:
            self.permissions = EnhancedRolePermissions(db)
        
        role = await self.permissions.get_user_role(user_id, organization_id)
        return role is not None
    
    async def check_project_access(
        self, 
        user_id: str, 
        project_id: str, 
        organization_id: str,
        db: AsyncSession
    ) -> bool:
        """Check if user has access to specific project"""
        if not self.permissions:
            self.permissions = EnhancedRolePermissions(db)
        
        accessible_projects = await self.permissions.get_accessible_projects(
            user_id, organization_id
        )
        return project_id in accessible_projects
    
    async def filter_projects_by_access(
        self, 
        user_id: str, 
        organization_id: str,
        db: AsyncSession
    ) -> list:
        """Get list of projects user can access"""
        if not self.permissions:
            self.permissions = EnhancedRolePermissions(db)
        
        return await self.permissions.get_accessible_projects(user_id, organization_id)
    
    async def get_dashboard_permissions(
        self, 
        user_id: str, 
        organization_id: str,
        db: AsyncSession
    ) -> dict:
        """Get dashboard permissions for user"""
        if not self.permissions:
            self.permissions = EnhancedRolePermissions(db)
        
        role = await self.permissions.get_user_role(user_id, organization_id)
        permissions = await self.permissions.get_user_permissions(user_id, organization_id)
        
        return {
            'role': role,
            'permissions': permissions,
            'can_create_projects': Permission.CREATE_PROJECT.value in permissions,
            'can_schedule_meetings': Permission.SCHEDULE_MEETING.value in permissions,
            'can_invite_members': Permission.INVITE_MEMBER.value in permissions,
            'can_manage_organization': Permission.MANAGE_ORGANIZATION.value in permissions,
            'can_view_all_projects': Permission.VIEW_ALL_PROJECTS.value in permissions,
            'can_assign_tasks': Permission.ASSIGN_TASK.value in permissions,
            'can_change_roles': Permission.PROMOTE_TO_MEMBER.value in permissions or Permission.PROMOTE_TO_ADMIN.value in permissions
        }


# Global middleware instance
rbac_middleware = RoleBasedAccessMiddleware()


# Dependency functions for FastAPI
async def get_rbac_middleware() -> RoleBasedAccessMiddleware:
    """Get RBAC middleware instance"""
    return rbac_middleware


async def require_organization_access(
    organization_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    rbac: RoleBasedAccessMiddleware = Depends(get_rbac_middleware)
):
    """Dependency to require organization access"""
    has_access = await rbac.check_organization_access(
        str(current_user.id), organization_id, db
    )
    
    if not has_access:
        raise HTTPException(
            status_code=403, 
            detail="Access denied to this organization"
        )
    
    return True


async def require_project_access(
    project_id: str,
    organization_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    rbac: RoleBasedAccessMiddleware = Depends(get_rbac_middleware)
):
    """Dependency to require project access"""
    has_access = await rbac.check_project_access(
        str(current_user.id), project_id, organization_id, db
    )
    
    if not has_access:
        raise HTTPException(
            status_code=403, 
            detail="Access denied to this project"
        )
    
    return True


async def get_user_dashboard_permissions(
    organization_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    rbac: RoleBasedAccessMiddleware = Depends(get_rbac_middleware)
) -> dict:
    """Get user's dashboard permissions"""
    return await rbac.get_dashboard_permissions(
        str(current_user.id), organization_id, db
    )


async def get_accessible_projects(
    organization_id: str,
    current_user: User,
    db: AsyncSession
) -> list:
    """Get projects accessible to user"""
    rbac = RoleBasedAccessMiddleware()
    return await rbac.filter_projects_by_access(
        str(current_user.id), organization_id, db
    )
