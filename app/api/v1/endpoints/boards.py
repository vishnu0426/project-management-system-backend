"""
Board management endpoints
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.deps import get_current_active_user
from app.core.exceptions import ResourceNotFoundError, InsufficientPermissionsError
from app.models.user import User
from app.models.organization import OrganizationMember
from app.models.project import Project
from app.models.board import Board
from app.models.column import Column
from app.schemas.project import BoardCreate, BoardUpdate, BoardResponse

router = APIRouter()


@router.get("/", response_model=List[BoardResponse])
async def get_boards(
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

        return [BoardResponse.from_orm(board) for board in boards]

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get boards: {str(e)}"
        )


@router.get("/{board_id}", response_model=BoardResponse)
async def get_board(
    board_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get board by ID"""
    result = await db.execute(
        select(Board)
        .options(selectinload(Board.project))
        .where(Board.id == board_id)
    )
    board = result.scalar_one_or_none()
    if not board:
        raise ResourceNotFoundError("Board not found")
    
    # Check access through organization membership
    org_member_result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == board.project.organization_id,
            OrganizationMember.user_id == current_user.id
        )
    )
    if not org_member_result.scalar_one_or_none():
        raise InsufficientPermissionsError("Access denied")
    
    return BoardResponse.from_orm(board)


@router.put("/{board_id}", response_model=BoardResponse)
async def update_board(
    board_id: str,
    board_data: BoardUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Update board"""
    result = await db.execute(
        select(Board)
        .options(selectinload(Board.project))
        .where(Board.id == board_id)
    )
    board = result.scalar_one_or_none()
    if not board:
        raise ResourceNotFoundError("Board not found")
    
    # Check access and permissions
    org_member_result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == board.project.organization_id,
            OrganizationMember.user_id == current_user.id
        )
    )
    org_member = org_member_result.scalar_one_or_none()
    if not org_member:
        raise InsufficientPermissionsError("Access denied")
    
    if org_member.role not in ['member', 'admin', 'owner']:
        raise InsufficientPermissionsError("Insufficient permissions")
    
    # Update fields
    if board_data.name is not None:
        board.name = board_data.name
    if board_data.description is not None:
        board.description = board_data.description
    
    await db.commit()
    await db.refresh(board)
    
    return BoardResponse.from_orm(board)


@router.delete("/{board_id}")
async def delete_board(
    board_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete board"""
    result = await db.execute(
        select(Board)
        .options(selectinload(Board.project))
        .where(Board.id == board_id)
    )
    board = result.scalar_one_or_none()
    if not board:
        raise ResourceNotFoundError("Board not found")
    
    # Check access and permissions
    org_member_result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == board.project.organization_id,
            OrganizationMember.user_id == current_user.id
        )
    )
    org_member = org_member_result.scalar_one_or_none()
    if not org_member:
        raise InsufficientPermissionsError("Access denied")
    
    if org_member.role not in ['admin', 'owner']:
        raise InsufficientPermissionsError("Insufficient permissions")

    # Check if project data is protected
    project = board.project
    if project.data_protected:
        # Only owners can delete boards from protected projects
        if org_member.role != 'owner':
            raise HTTPException(
                status_code=403,
                detail=f"Cannot delete board: Project data is protected. Reason: {project.protection_reason or 'Data protection enabled'}"
            )

        # Even owners get a warning about protected data
        if project.sign_off_requested and not project.sign_off_approved:
            raise HTTPException(
                status_code=403,
                detail="Cannot delete board: Project is pending sign-off approval. Complete the sign-off process first."
            )

    await db.delete(board)
    await db.commit()

    return {"success": True, "message": "Board deleted successfully"}


@router.get("/{project_id}/boards", response_model=List[BoardResponse])
async def get_project_boards(
    project_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get boards for a project"""
    # Check project access
    project_result = await db.execute(
        select(Project).where(Project.id == project_id)
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
    if not org_member_result.scalar_one_or_none():
        raise InsufficientPermissionsError("Access denied")
    
    # Get boards
    result = await db.execute(
        select(Board)
        .where(Board.project_id == project_id)
        .order_by(Board.created_at)
    )
    boards = result.scalars().all()
    
    return [BoardResponse.from_orm(board) for board in boards]


@router.post("/{project_id}/boards", response_model=BoardResponse)
async def create_board(
    project_id: str,
    board_data: BoardCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new board"""
    # Check project access
    project_result = await db.execute(
        select(Project).where(Project.id == project_id)
    )
    project = project_result.scalar_one_or_none()
    if not project:
        raise ResourceNotFoundError("Project not found")
    
    # Check organization membership and permissions using enhanced RBAC
    from app.services.enhanced_role_permissions import EnhancedRolePermissions, Permission
    permissions = EnhancedRolePermissions(db)

    organization_id = str(project.organization_id)
    user_role = await permissions.get_user_role(str(current_user.id), organization_id)

    if not user_role:
        raise InsufficientPermissionsError("Access denied")

    # Check if user can create boards
    can_create = await permissions.check_permission(
        str(current_user.id),
        organization_id,
        Permission.CREATE_BOARD
    )

    if not can_create:
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to create boards"
        )
    
    # Create board
    board = Board(
        project_id=project_id,
        name=board_data.name,
        description=board_data.description,
        created_by=current_user.id
    )
    
    db.add(board)
    await db.commit()
    await db.refresh(board)
    
    return BoardResponse.from_orm(board)


# New endpoint: flat board creation
#
# The front‑end often calls `POST /api/v1/boards` with a JSON body
# containing `name` and `project_id`.  The original board creation
# endpoint required the project ID to be part of the URL
# (`/projects/{project_id}/boards`).  To support both patterns, this
# handler accepts a `BoardCreate` payload that includes a
# `project_id`.  If `project_id` is missing, this will return a 400.
async def create_board_flat_internal(
    board_data: BoardCreate,
    current_user: User,
    db: AsyncSession
) -> BoardResponse:
    """Internal helper to create a board via a flat payload.

    This function mirrors the logic of the nested board creation endpoint
    but accepts a `BoardCreate` object that includes a `project_id`.  It
    returns a `BoardResponse` on success and raises appropriate exceptions
    on failure.  It is not exposed directly as an API route; instead,
    top‑level router aliases delegate to this helper to avoid path
    conflicts when the boards router is mounted under multiple prefixes.
    """
    if not board_data.project_id:
        # If the client did not provide a project_id, return an error
        raise HTTPException(
            status_code=400,
            detail="project_id is required when creating a board via this endpoint"
        )

    # Retrieve the project
    project_result = await db.execute(
        select(Project).where(Project.id == board_data.project_id)
    )
    project = project_result.scalar_one_or_none()
    if not project:
        raise ResourceNotFoundError("Project not found")

    # Check organization membership and permissions
    org_member_result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == project.organization_id,
            OrganizationMember.user_id == current_user.id
        )
    )
    org_member = org_member_result.scalar_one_or_none()
    if not org_member:
        raise InsufficientPermissionsError("Access denied")

    if org_member.role not in ['member', 'admin', 'owner']:
        raise InsufficientPermissionsError("Insufficient permissions")

    # Create the board
    board = Board(
        project_id=board_data.project_id,
        name=board_data.name,
        description=board_data.description,
        created_by=current_user.id
    )

    db.add(board)
    await db.commit()
    await db.refresh(board)

    # Create default columns for the board
    default_columns = [
        {"name": "To‑Do", "position": 0, "color": "#E5E7EB"},
        {"name": "In Progress", "position": 1, "color": "#DBEAFE"},
        {"name": "Review", "position": 2, "color": "#FEF3C7"},
        {"name": "Done", "position": 3, "color": "#D1FAE5"},
    ]

    for column_data in default_columns:
        column = Column(
            board_id=board.id,
            name=column_data["name"],
            position=column_data["position"],
            color=column_data["color"]
        )
        db.add(column)

    await db.commit()

    return BoardResponse.from_orm(board)


@router.put("/{board_id}", response_model=BoardResponse)
async def update_board(
    board_id: str,
    board_data: BoardUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Update board"""
    result = await db.execute(
        select(Board)
        .options(selectinload(Board.project))
        .where(Board.id == board_id)
    )
    board = result.scalar_one_or_none()
    if not board:
        raise ResourceNotFoundError("Board not found")

    # Check access and permissions using enhanced RBAC
    from app.services.enhanced_role_permissions import EnhancedRolePermissions
    permissions = EnhancedRolePermissions(db)

    organization_id = str(board.project.organization_id)
    user_role = await permissions.get_user_role(str(current_user.id), organization_id)

    if not user_role:
        raise InsufficientPermissionsError("Access denied")

    # Check if user can modify this board (ownership-based for members)
    can_modify = await permissions.can_modify_resource(
        str(current_user.id),
        organization_id,
        'board',
        board_id
    )

    if not can_modify:
        raise HTTPException(
            status_code=403,
            detail="You can only modify boards you created"
        )

    # Update board
    if board_data.name is not None:
        board.name = board_data.name
    if board_data.description is not None:
        board.description = board_data.description

    await db.commit()
    return board


@router.delete("/{board_id}")
async def delete_board(
    board_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete board"""
    result = await db.execute(
        select(Board)
        .options(selectinload(Board.project))
        .where(Board.id == board_id)
    )
    board = result.scalar_one_or_none()
    if not board:
        raise ResourceNotFoundError("Board not found")

    # Check access and permissions using enhanced RBAC
    from app.services.enhanced_role_permissions import EnhancedRolePermissions
    permissions = EnhancedRolePermissions(db)

    organization_id = str(board.project.organization_id)
    user_role = await permissions.get_user_role(str(current_user.id), organization_id)

    if not user_role:
        raise InsufficientPermissionsError("Access denied")

    # Check if user can modify this board (ownership-based for members)
    can_modify = await permissions.can_modify_resource(
        str(current_user.id),
        organization_id,
        'board',
        board_id
    )

    if not can_modify:
        raise HTTPException(
            status_code=403,
            detail="You can only delete boards you created"
        )

    # Delete the board
    await db.delete(board)
    await db.commit()

    return {"message": "Board deleted successfully"}
