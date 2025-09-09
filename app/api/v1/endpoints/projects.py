"""
Project management endpoints
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.deps import get_current_active_user, get_organization_member, get_organization_member_by_path, require_member, require_member_by_path, require_organization_role
from app.core.exceptions import ValidationError, ResourceNotFoundError, InsufficientPermissionsError
from app.core.permissions import can_create_projects, get_user_role_in_organization
from app.models.user import User
from app.models.organization import OrganizationMember
from app.models.project import Project
from app.schemas.project import ProjectCreate, ProjectUpdate, ProjectResponse, EnhancedProjectCreate, EnhancedProjectResponse
from app.services.organization_service import OrganizationService
from app.middleware.role_based_access import require_permission, get_accessible_projects, require_organization_access, get_rbac_middleware, RoleBasedAccessMiddleware
from app.services.enhanced_role_permissions import Permission
from app.services.email_service import email_service

router = APIRouter()


async def check_organization_member(db: AsyncSession, organization_id: str, user_id: str):
    """Helper function to check if user is member of organization"""
    result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.user_id == user_id
        )
    )
    return result.scalar_one_or_none()


async def require_organization_member_query(
    organization_id: str = Query(...),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> OrganizationMember:
    """Dependency to require organization membership using query parameter"""
    org_member = await check_organization_member(db, organization_id, current_user.id)
    if not org_member:
        raise InsufficientPermissionsError("Organization membership required")
    return org_member


@router.get("", response_model=List[ProjectResponse])
async def get_projects(
    organization_id: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get projects for user with organization-specific filtering"""
    offset = (page - 1) * limit
    org_service = OrganizationService(db)

    # Get current organization if not specified
    if not organization_id:
        organization_id = await org_service.get_current_organization(str(current_user.id))
        if not organization_id:
            raise HTTPException(status_code=400, detail="No organization context")

    # Check organization access
    rbac = await get_rbac_middleware()
    has_access = await rbac.check_organization_access(
        str(current_user.id), organization_id, db
    )

    if not has_access:
        raise HTTPException(
            status_code=403,
            detail="Access denied to this organization"
        )

    # Get accessible projects based on user role
    accessible_project_ids = await get_accessible_projects(organization_id, current_user, db)

    if not accessible_project_ids:
        return []

    # Get projects with proper filtering and optimized query
    result = await db.execute(
        select(Project)
        .where(
            and_(
                Project.organization_id == organization_id,
                Project.id.in_(accessible_project_ids)
            )
        )
        .offset(offset)
        .limit(limit)
        .order_by(Project.created_at.desc())
    )

    projects = result.scalars().all()
    return [ProjectResponse.from_orm(project) for project in projects]


@router.post("", response_model=ProjectResponse)
@require_permission(Permission.CREATE_PROJECT)
async def create_project(
    project_data: ProjectCreate,
    organization_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new project with organization-specific access control"""
    # Verify organization access
    rbac = RoleBasedAccessMiddleware()
    has_access = await rbac.check_organization_access(
        str(current_user.id), organization_id, db
    )

    if not has_access:
        raise HTTPException(
            status_code=403,
            detail="Access denied to this organization"
        )

    # Get organization details for email
    org_result = await db.execute(
        select(OrganizationMember)
        .options(selectinload(OrganizationMember.organization))
        .where(OrganizationMember.organization_id == organization_id)
        .where(OrganizationMember.user_id == current_user.id)
    )
    org_member = org_result.scalar_one_or_none()

    # Create project
    project = Project(
        organization_id=organization_id,
        name=project_data.name,
        description=project_data.description,
        status=project_data.status,
        priority=project_data.priority,
        start_date=project_data.start_date,
        due_date=project_data.due_date,
        created_by=current_user.id
    )

    db.add(project)
    await db.commit()
    await db.refresh(project)

    # Send project creation confirmation email
    if org_member and org_member.organization:
        project_email_data = {
            "name": project.name,
            "description": project.description,
            "status": project.status,
            "priority": project.priority,
            "start_date": project.start_date.isoformat() if project.start_date else None,
            "due_date": project.due_date.isoformat() if project.due_date else None,
            "created_at": project.created_at.isoformat() if project.created_at else None,
            "project_id": str(project.id)
        }

        background_tasks.add_task(
            email_service.send_project_creation_confirmation,
            current_user.email,
            f"{current_user.first_name} {current_user.last_name}",
            project_email_data,
            org_member.organization.name
        )

    return ProjectResponse.from_orm(project)


@router.post("/enhanced", response_model=EnhancedProjectResponse)
async def create_enhanced_project(
    project_data: EnhancedProjectCreate,
    organization_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new enhanced project with full configuration"""
    # Check user's role in the organization
    user_role = await get_user_role_in_organization(current_user.id, organization_id, db)

    if not user_role:
        raise InsufficientPermissionsError("User is not a member of this organization")

    if not can_create_projects(user_role):
        raise InsufficientPermissionsError(f"Role '{user_role}' does not have permission to create projects")

    # Convert Pydantic models to dict for JSON storage
    configuration_data = project_data.configuration.dict() if project_data.configuration else None
    overview_data = project_data.overview.dict() if project_data.overview else None
    tech_stack_data = project_data.tech_stack.dict() if project_data.tech_stack else None
    workflow_data = project_data.workflow.dict() if project_data.workflow else None
    tasks_data = [task.dict() for task in project_data.tasks] if project_data.tasks else None

    project = Project(
        organization_id=organization_id,
        name=project_data.name,
        description=project_data.description,
        status=project_data.status,
        priority=project_data.priority,
        start_date=project_data.start_date,
        due_date=project_data.due_date,
        created_by=current_user.id,
        configuration=configuration_data,
        overview=overview_data,
        tech_stack=tech_stack_data,
        workflow=workflow_data,
        tasks=tasks_data,
        notifications=project_data.notifications,
        launch_options=project_data.launch_options,
        finalized_at=project_data.finalized_at
    )

    db.add(project)
    await db.commit()
    await db.refresh(project)

    # Send project creation confirmation email
    org_result = await db.execute(
        select(OrganizationMember)
        .options(selectinload(OrganizationMember.organization))
        .where(OrganizationMember.organization_id == organization_id)
        .where(OrganizationMember.user_id == current_user.id)
    )
    org_member = org_result.scalar_one_or_none()

    if org_member and org_member.organization:
        project_email_data = {
            "name": project.name,
            "description": project.description,
            "status": project.status,
            "priority": project.priority,
            "start_date": project.start_date.isoformat() if project.start_date else None,
            "due_date": project.due_date.isoformat() if project.due_date else None,
            "created_at": project.created_at.isoformat() if project.created_at else None,
            "project_id": str(project.id),
            "enhanced": True,
            "tasks_count": len(project_data.tasks) if project_data.tasks else 0,
            "tech_stack": tech_stack_data,
            "workflow_phases": workflow_data.get("phases", []) if workflow_data else []
        }

        background_tasks.add_task(
            email_service.send_project_creation_confirmation,
            current_user.email,
            f"{current_user.first_name} {current_user.last_name}",
            project_email_data,
            org_member.organization.name
        )

    return EnhancedProjectResponse.from_orm(project)


@router.get("/{project_id}/enhanced", response_model=EnhancedProjectResponse)
async def get_enhanced_project(
    project_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get enhanced project with all configuration data"""
    result = await db.execute(
        select(Project).where(Project.id == project_id)
    )
    project = result.scalar_one_or_none()

    if not project:
        raise ResourceNotFoundError("Project not found")

    # Check if user has access to this project
    org_member = await check_organization_member(db, project.organization_id, current_user.id)
    if not org_member:
        raise InsufficientPermissionsError("Access denied")

    return EnhancedProjectResponse.from_orm(project)


@router.put("/{project_id}/configuration")
async def update_project_configuration(
    project_id: str,
    configuration_data: dict,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Update project configuration data"""
    result = await db.execute(
        select(Project).where(Project.id == project_id)
    )
    project = result.scalar_one_or_none()

    if not project:
        raise ResourceNotFoundError("Project not found")

    # Check permissions
    org_member = await check_organization_member(db, project.organization_id, current_user.id)
    if not org_member or org_member.role not in ['owner', 'admin']:
        raise InsufficientPermissionsError("Insufficient permissions")

    project.configuration = configuration_data
    await db.commit()
    await db.refresh(project)

    return {"success": True, "message": "Configuration updated successfully"}


@router.put("/{project_id}/workflow")
async def update_project_workflow(
    project_id: str,
    workflow_data: dict,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Update project workflow data"""
    result = await db.execute(
        select(Project).where(Project.id == project_id)
    )
    project = result.scalar_one_or_none()

    if not project:
        raise ResourceNotFoundError("Project not found")

    # Check permissions
    org_member = await check_organization_member(db, project.organization_id, current_user.id)
    if not org_member or org_member.role not in ['owner', 'admin']:
        raise InsufficientPermissionsError("Insufficient permissions")

    project.workflow = workflow_data
    await db.commit()
    await db.refresh(project)

    return {"success": True, "message": "Workflow updated successfully"}


@router.put("/{project_id}/tasks")
async def update_project_tasks(
    project_id: str,
    tasks_data: List[dict],
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Update project tasks data"""
    result = await db.execute(
        select(Project).where(Project.id == project_id)
    )
    project = result.scalar_one_or_none()

    if not project:
        raise ResourceNotFoundError("Project not found")

    # Check permissions
    org_member = await check_organization_member(db, project.organization_id, current_user.id)
    if not org_member:
        raise InsufficientPermissionsError("Access denied")

    project.tasks = tasks_data
    await db.commit()
    await db.refresh(project)

    return {"success": True, "message": "Tasks updated successfully"}


@router.post("/{project_id}/finalize")
async def finalize_project(
    project_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Finalize project and mark as launched"""
    result = await db.execute(
        select(Project).where(Project.id == project_id)
    )
    project = result.scalar_one_or_none()

    if not project:
        raise ResourceNotFoundError("Project not found")

    # Check permissions
    org_member = await check_organization_member(db, project.organization_id, current_user.id)
    if not org_member or org_member.role not in ['owner', 'admin']:
        raise InsufficientPermissionsError("Insufficient permissions")

    from datetime import datetime
    project.finalized_at = datetime.utcnow()
    await db.commit()
    await db.refresh(project)

    return {"success": True, "message": "Project finalized successfully", "finalized_at": project.finalized_at}


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get project by ID"""
    result = await db.execute(
        select(Project).where(Project.id == project_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise ResourceNotFoundError("Project not found")
    
    # Check if user has access to this project's organization
    org_member_result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == project.organization_id,
            OrganizationMember.user_id == current_user.id
        )
    )
    if not org_member_result.scalar_one_or_none():
        raise InsufficientPermissionsError("Access denied")
    
    return ProjectResponse.from_orm(project)


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    project_data: ProjectUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Update project"""
    result = await db.execute(
        select(Project).where(Project.id == project_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise ResourceNotFoundError("Project not found")
    
    # Check if user has access to this project's organization
    org_member_result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == project.organization_id,
            OrganizationMember.user_id == current_user.id
        )
    )
    org_member = org_member_result.scalar_one_or_none()
    if not org_member:
        raise InsufficientPermissionsError("Access denied")
    
    # Check permissions (member or above can edit)
    if org_member.role not in ['member', 'admin', 'owner']:
        raise InsufficientPermissionsError("Insufficient permissions to edit project")
    
    # Update fields if provided
    if project_data.name is not None:
        project.name = project_data.name
    if project_data.description is not None:
        project.description = project_data.description
    if project_data.status is not None:
        project.status = project_data.status
    if project_data.priority is not None:
        project.priority = project_data.priority
    if project_data.start_date is not None:
        project.start_date = project_data.start_date
    if project_data.due_date is not None:
        project.due_date = project_data.due_date
    
    await db.commit()
    await db.refresh(project)
    
    return ProjectResponse.from_orm(project)


@router.delete("/{project_id}")
async def delete_project(
    project_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete project"""
    result = await db.execute(
        select(Project).where(Project.id == project_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise ResourceNotFoundError("Project not found")
    
    # Check if user has access to this project's organization
    org_member_result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == project.organization_id,
            OrganizationMember.user_id == current_user.id
        )
    )
    org_member = org_member_result.scalar_one_or_none()
    if not org_member:
        raise InsufficientPermissionsError("Access denied")
    
    # Check permissions (admin or above can delete)
    if org_member.role not in ['admin', 'owner']:
        raise InsufficientPermissionsError("Insufficient permissions to delete project")
    
    # Delete project (cascade will handle boards, columns, cards, etc.)
    await db.delete(project)
    await db.commit()
    
    return {"success": True, "message": "Project deleted successfully"}


@router.get("/debug/permissions")
async def debug_user_permissions(
    organization_id: str = Query(..., description="Organization ID to check permissions for"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Debug endpoint to check user's project creation permissions"""
    from app.models.organization_settings import OrganizationSettings
    from app.services.enhanced_role_permissions import EnhancedRolePermissions

    # Get user's role in organization
    result = await db.execute(
        select(OrganizationMember.role)
        .where(
            and_(
                OrganizationMember.organization_id == organization_id,
                OrganizationMember.user_id == current_user.id
            )
        )
    )

    user_role = result.scalar_one_or_none()

    # Get organization settings
    settings_result = await db.execute(
        select(OrganizationSettings)
        .where(OrganizationSettings.organization_id == organization_id)
    )

    settings = settings_result.scalar_one_or_none()

    # Check permissions using the enhanced role permissions service
    permissions_service = EnhancedRolePermissions(db)
    can_create = await permissions_service.check_permission(
        str(current_user.id),
        organization_id,
        Permission.CREATE_PROJECT
    )

    return {
        "user_id": str(current_user.id),
        "organization_id": organization_id,
        "user_role": user_role,
        "can_create_projects": can_create,
        "organization_settings": {
            "allow_admin_create_projects": settings.allow_admin_create_projects if settings else None,
            "allow_member_create_projects": settings.allow_member_create_projects if settings else None,
        } if settings else "No settings found",
        "recommendation": (
            "User can create projects" if can_create else
            f"User cannot create projects. Role: {user_role}. " +
            ("Enable 'allow_member_create_projects' in organization settings" if user_role == 'member' else
             "Enable 'allow_admin_create_projects' in organization settings" if user_role == 'admin' else
             "User should be assigned owner, admin, or member role")
        )
    }
