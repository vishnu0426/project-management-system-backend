"""
Main API router for v1 endpoints
"""
from fastapi import APIRouter

from app.api.v1.endpoints import auth, users, organizations, projects, boards, columns, cards, teams, upload, checklist, ai_projects, meetings, task_dependencies, notifications, registration, project_signoff, kanban, health, files
from app.api.v1.endpoints import organizations_enhanced, projects_enhanced, dashboard_api, task_assignment
from app.api.v1 import organization_hierarchy, bulk_operations, analytics, security, integrations, ai_automation

api_router = APIRouter(prefix="/v1")


@api_router.get("/")
async def api_root():
    """API v1 root endpoint"""
    return {
        "success": True,
        "data": {
            "message": "Agno WorkSphere API v1",
            "version": "1.0.0",
            "endpoints": {
                "auth": "/api/v1/auth",
                "users": "/api/v1/users",
                "organizations": "/api/v1/organizations",
                "projects": "/api/v1/projects",
                "boards": "/api/v1/boards",
                "columns": "/api/v1/columns",
                "cards": "/api/v1/cards",
                "teams": "/api/v1/teams",
                "analytics": "/api/v1/analytics",
                "ai": "/api/v1/ai",
                "ai_projects": "/api/v1/ai-projects",
                "meetings": "/api/v1/meetings",
                "dependencies": "/api/v1/dependencies",
                "notifications": "/api/v1/notifications",
                "registrations": "/api/v1/registrations",
                "project_signoff": "/api/v1/project-signoff"
            }
        },
        "timestamp": __import__('time').time()
    }


# Include all endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(organizations.router, prefix="/organizations", tags=["Organizations"])
api_router.include_router(projects.router, prefix="/projects", tags=["Projects"])

# Mount boards router under /boards for individual board operations
# This provides GET/PUT/DELETE /boards/{board_id} endpoints
api_router.include_router(boards.router, prefix="/boards", tags=["Boards"])
api_router.include_router(columns.router, prefix="/columns", tags=["Columns"])
api_router.include_router(cards.router, prefix="/cards", tags=["Cards"])
api_router.include_router(kanban.router, prefix="/kanban", tags=["Kanban Board"])
api_router.include_router(checklist.router, prefix="/checklist", tags=["Checklist & AI"])
api_router.include_router(teams.router, prefix="/teams", tags=["Teams"])
api_router.include_router(upload.router, prefix="/upload", tags=["File Upload"])
api_router.include_router(files.router, prefix="/files", tags=["Files"])
api_router.include_router(organization_hierarchy.router, prefix="/hierarchy", tags=["Organization Hierarchy"])
api_router.include_router(bulk_operations.router, prefix="/bulk", tags=["Bulk Operations"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["Analytics & Reporting"])
api_router.include_router(security.router, prefix="/security", tags=["Security & Compliance"])
api_router.include_router(integrations.router, prefix="/integrations", tags=["Integrations"])
api_router.include_router(ai_automation.router, prefix="/ai", tags=["AI & Automation"])
api_router.include_router(ai_projects.router, prefix="/ai-projects", tags=["AI Projects"])
api_router.include_router(meetings.router, prefix="/meetings", tags=["Meetings"])
api_router.include_router(task_dependencies.router, prefix="/dependencies", tags=["Task Dependencies"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["Notifications"])
api_router.include_router(registration.router, prefix="/registrations", tags=["Registration Management"])
api_router.include_router(project_signoff.router, prefix="/project-signoff", tags=["Project Sign-off"])
api_router.include_router(health.router, tags=["Health"])

# -----------------------------------------------------------------------------
# Alias routes for commonly used paths that span multiple routers
#
# Certain front-end clients expect to access resources using a flatter URL
# structure than the one originally defined.  For example, the Kanban board
# page calls `GET /api/v1/boards/{boardId}/columns` to fetch columns for a
# board.  However, the columns router is mounted under the `/columns` prefix
# (yielding `/api/v1/columns/{boardId}/columns` for the nested route), so
# hitting `/api/v1/boards/{boardId}/columns` would normally result in a 404.
# To bridge this gap, we define a small wrapper route here that forwards
# requests from the flat path to the appropriate handler in the columns
# module.  This keeps the implementation centralized in `columns.py` while
# avoiding duplicate business logic.

from typing import List
from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.deps import get_current_active_user, get_db
from app.models.user import User
from app.models.organization import OrganizationMember
from app.models.project import Project
from app.models.board import Board
from app.api.v1.endpoints.columns import get_board_columns, create_column

from app.api.v1.endpoints.boards import create_board_flat_internal, get_project_boards as _get_project_boards, create_board as _create_board
from app.schemas.project import BoardCreate, ColumnCreate
from app.api.v1.endpoints.boards import BoardResponse as _BoardResponse


@api_router.get("/boards/{board_id}/columns", tags=["Columns"], response_model=List[columns.ColumnResponse])
async def get_board_columns_flat(
    board_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Alias endpoint: Get columns for a board via the `/boards/{board_id}/columns` path.

    This wrapper simply delegates to the existing `get_board_columns` handler defined
    in `app.api.v1.endpoints.columns`.  It allows clients to fetch columns via
    `/api/v1/boards/{boardId}/columns` instead of the original nested
    `/api/v1/columns/{boardId}/columns` route.  The authorization and
    organization membership checks are performed in the underlying handler.
    """
    return await get_board_columns(board_id=board_id, current_user=current_user, db=db)

@api_router.post("/boards/{board_id}/columns", tags=["Columns"], response_model=columns.ColumnResponse)
async def create_board_column_flat(
    board_id: str,
    column_data: ColumnCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Alias endpoint: Create a column under a board via `/boards/{board_id}/columns`."""
    return await create_column(board_id=board_id, column_data=column_data, current_user=current_user, db=db)

# -----------------------------------------------------------------------------
# Project-scoped board routes (aliases)
#
# Register project-scoped board endpoints here to avoid mounting the boards
# router under `/projects`, which conflicted with project routes.

@api_router.get("/projects/{project_id}/boards", tags=["Boards"], response_model=List[_BoardResponse])
async def get_boards_for_project(
    project_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    return await _get_project_boards(project_id=project_id, current_user=current_user, db=db)

@api_router.post("/projects/{project_id}/boards", tags=["Boards"], response_model=_BoardResponse)
async def create_board_for_project(
    project_id: str,
    board_data: BoardCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    return await _create_board(project_id=project_id, board_data=board_data, current_user=current_user, db=db)

# -----------------------------------------------------------------------------
# Board alias routes
#
# The front‑end creates new boards via `POST /api/v1/boards` with a payload
# containing `name`, `project_id`, and optional `description`.  The original
# implementation exposed only a nested endpoint (`/projects/{project_id}/boards`)
# and a conflicting flat endpoint mounted under `/projects`.  To support the
# flat creation pattern without path conflicts, we register a dedicated
# top‑level route here that delegates to an internal helper defined in
# `boards.py`.

@api_router.get("/boards", tags=["Boards"], response_model=List[_BoardResponse])
async def get_all_boards(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all boards accessible to the current user"""
    try:
        # Get user's organizations
        org_member_result = await db.execute(
            select(OrganizationMember.organization_id)
            .where(OrganizationMember.user_id == current_user.id)
        )
        org_ids = [row[0] for row in org_member_result.fetchall()]

        if not org_ids:
            return []

        # Get boards from user's organizations
        result = await db.execute(
            select(Board)
            .options(selectinload(Board.project))
            .join(Project)
            .where(Project.organization_id.in_(org_ids))
            .order_by(Board.created_at.desc())
        )
        boards = result.scalars().all()

        return [_BoardResponse.from_orm(board) for board in boards]

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get boards: {str(e)}"
        )

@api_router.post("/boards", tags=["Boards"], response_model=_BoardResponse)
async def create_board_flat_router(
    board_data: BoardCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new board via the `/boards` endpoint.

    This wrapper delegates to `create_board_flat_internal` defined in
    `app.api.v1.endpoints.boards`.  It ensures that the flat `POST /boards` path
    does not collide with other routes mounted under `/projects`.
    """
    return await create_board_flat_internal(board_data=board_data, current_user=current_user, db=db)

# Enhanced Multi-Organization Endpoints
api_router.include_router(organizations_enhanced.router, prefix="/organizations-enhanced", tags=["Enhanced Organizations"])
api_router.include_router(projects_enhanced.router, prefix="/projects-enhanced", tags=["Enhanced Projects"])
api_router.include_router(dashboard_api.router, prefix="/dashboard", tags=["Role-Based Dashboard"])
api_router.include_router(task_assignment.router, prefix="/task-assignment", tags=["Task Assignment & Notifications"])
