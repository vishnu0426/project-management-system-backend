"""
File management endpoints

This module provides a set of simplified file management endpoints that
the front‑end expects under the `/files` prefix.  While the existing
`upload` module implements upload and deletion logic for avatars,
organization logos and card attachments, the front‑end also calls
`/api/v1/files/upload` to attach files to cards, `/api/v1/files?card_id=…`
to list card attachments and `/api/v1/files/{file_id}` to delete
attachments.  Those routes did not previously exist which led to 404
errors.  The handlers below delegate to the same validation and
storage helpers used by the upload module and perform minimal
authorization checks to ensure that only members of a card’s
organization can view or manipulate its attachments.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, UploadFile, File, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.deps import get_current_active_user
from app.core.exceptions import ValidationError, ResourceNotFoundError, InsufficientPermissionsError
from app.models.user import User
from app.models.card import Card
from app.models.column import Column
from app.models.board import Board
from app.models.project import Project
from app.models.organization import OrganizationMember
from app.models.attachment import Attachment
from app.api.v1.endpoints.upload import validate_file, save_file, generate_filename

# Create a dedicated router for file operations.  This router will be
# mounted under the `/files` prefix by the main API router.
router = APIRouter()


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    card_id: Optional[str] = Query(None, description="The ID of the card this file should be attached to"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload a file and optionally associate it with a card.

    The front‑end always provides a `card_id` when uploading
    attachments.  Without a card ID we cannot create a database record
    because the Attachment model requires a non‑null `card_id`.  If
    `card_id` is omitted a validation error is returned.
    """
    # Validate that a file has been provided and that it meets
    # security requirements (size, extension, MIME type, etc.).
    validate_file(file)

    # Ensure a card identifier was supplied.  Without this we cannot
    # associate the upload with a task.  Returning a ValidationError
    # keeps behaviour consistent with other endpoints.
    if not card_id:
        raise ValidationError("card_id is required for file uploads")

    # Verify that the referenced card exists.
    card_result = await db.execute(select(Card).where(Card.id == card_id))
    card = card_result.scalar_one_or_none()
    if not card:
        raise ResourceNotFoundError("Card not found")

    # TODO: check if user has permission to attach files to this card.
    # For now we simply require that the user be a member of the
    # organization that owns the card.  The organization can be found
    # by traversing from card -> column -> board -> project.
    project = None
    if card and card.column:
        # Load associated board/project if relationship is already loaded
        # otherwise explicitly query for it.  We avoid expensive
        # joins unless necessary.
        if getattr(card.column, "board", None) and getattr(card.column.board, "project", None):
            project = card.column.board.project
        else:
            project_result = await db.execute(
                select(Project)
                .join(Board, Board.project_id == Project.id)
                .join(Column, Column.board_id == Board.id)
                .join(Card, Card.column_id == Column.id)
                .where(Card.id == card_id)
            )
            project = project_result.scalar_one_or_none()

    if project:
        org_member_result = await db.execute(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == project.organization_id,
                OrganizationMember.user_id == current_user.id,
            )
        )
        if not org_member_result.scalar_one_or_none():
            raise InsufficientPermissionsError("Access denied")

    # Persist the file to disk.  The save_file helper creates a unique
    # filename and writes the contents to disk under the chosen
    # directory.  It returns a URL relative to the /uploads mount.
    directory = f"uploads/attachments/{card_id}"
    file_url = await save_file(file, directory)

    # Generate a new filename for the attachment record.  We call
    # generate_filename separately from save_file to mirror the logic
    # used in the existing upload endpoints.  This means the
    # filename stored in the database may differ from the filename on
    # disk, but both values are unique and avoid collisions.
    new_filename = generate_filename(file.filename)

    # Create the attachment record.  SQLAlchemy will generate a UUID
    # for the attachment ID.  We record both the generated filename
    # and the original client‑provided name for display purposes.
    attachment = Attachment(
        card_id=card_id,
        filename=new_filename,
        original_name=file.filename,
        file_size=file.size or 0,
        mime_type=file.content_type or "application/octet-stream",
        file_url=file_url,
        uploaded_by=current_user.id,
    )

    db.add(attachment)
    await db.commit()
    await db.refresh(attachment)

    # Return a consistent response payload.  The front‑end expects
    # fields like `id`, `original_name` and `file_url`.
    return {
        "success": True,
        "data": {
            "attachment": {
                "id": str(attachment.id),
                "filename": attachment.filename,
                "original_name": attachment.original_name,
                "file_size": attachment.file_size,
                "mime_type": attachment.mime_type,
                "file_url": attachment.file_url,
                "uploaded_at": attachment.uploaded_at.isoformat(),
            }
        },
        "message": "File uploaded successfully",
    }


@router.get("")
async def list_files(
    card_id: Optional[str] = Query(None, description="Filter attachments by card ID"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """List attachments for a given card.

    If no `card_id` is provided, an empty list is returned.  When a
    card ID is provided we verify that the current user belongs to
    the organization owning the card before returning attachment
    metadata.
    """
    # Without a card ID there is nothing to return.  This keeps the
    # behaviour explicit and avoids accidentally leaking attachments
    # across cards.
    if not card_id:
        return {"success": True, "data": []}

    # Fetch attachments along with their related card/column/board/project
    # in one query for efficient authorization checks.
    result = await db.execute(
        select(Attachment)
        .options(
            selectinload(Attachment.card)
            .selectinload(Card.column)
            .selectinload(Column.board)
            .selectinload(Board.project)
        )
        .where(Attachment.card_id == card_id)
    )
    attachments = result.scalars().all()

    # If there are no attachments, we can return early without
    # performing an authorization check.
    if not attachments:
        return {"success": True, "data": []}

    # Determine the organization associated with the card.  Since all
    # attachments belong to the same card, we can use the first
    # attachment’s card to find the project and thus the organization.
    sample_attachment = attachments[0]
    project = sample_attachment.card.column.board.project if sample_attachment.card and sample_attachment.card.column and sample_attachment.card.column.board else None
    if project:
        org_member_result = await db.execute(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == project.organization_id,
                OrganizationMember.user_id == current_user.id,
            )
        )
        if not org_member_result.scalar_one_or_none():
            raise InsufficientPermissionsError("Access denied")

    # Build the response list.  We expose only the fields needed by
    # the front‑end and cast UUIDs to strings for JSON serialization.
    files_data = []
    for att in attachments:
        files_data.append({
            "id": str(att.id),
            "filename": att.filename,
            "original_name": att.original_name,
            "file_size": att.file_size,
            "mime_type": att.mime_type,
            "file_url": att.file_url,
            "uploaded_at": att.uploaded_at.isoformat(),
            "uploaded_by": str(att.uploaded_by),
        })

    return {"success": True, "data": files_data}


@router.delete("/{file_id}")
async def remove_file(
    file_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete an uploaded file by its ID.

    This endpoint mirrors the deletion logic of the `/upload/{file_id}`
    endpoint but is mounted under `/files` so that the front‑end can
    call `/api/v1/files/{fileId}`.  It verifies that the user has
    permissions to delete the attachment before removing it from both
    the database and the file system.
    """
    # Fetch attachment along with project information for permission checks.
    attachment_result = await db.execute(
        select(Attachment)
        .options(
            selectinload(Attachment.card)
            .selectinload(Card.column)
            .selectinload(Column.board)
            .selectinload(Board.project)
        )
        .where(Attachment.id == file_id)
    )
    attachment = attachment_result.scalar_one_or_none()
    if not attachment:
        raise ResourceNotFoundError("File not found")

    # Ensure the user is a member of the organization that owns this card.
    project = attachment.card.column.board.project if attachment.card and attachment.card.column and attachment.card.column.board else None
    if project:
        org_member_result = await db.execute(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == project.organization_id,
                OrganizationMember.user_id == current_user.id,
            )
        )
        org_member = org_member_result.scalar_one_or_none()
        if not org_member:
            raise InsufficientPermissionsError("Access denied")

        # If the project has data protection enabled only owners may delete.
        if getattr(project, "data_protected", False):
            if org_member.role != "owner":
                raise InsufficientPermissionsError("Cannot delete attachment: Project data is protected")
            # Additional sign‑off check similar to upload.delete_file
            if getattr(project, "sign_off_requested", False) and not getattr(project, "sign_off_approved", False):
                raise InsufficientPermissionsError("Cannot delete attachment: Project is pending sign‑off approval")

    # Remove the file from disk.  We attempt to delete quietly even if
    # the file is missing.
    import os

    file_path = f"uploads{attachment.file_url.replace('/uploads', '')}"
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception:
        # Ignore deletion errors; the database record will still be removed.
        pass

    # Remove the record from the database.
    await db.delete(attachment)
    await db.commit()

    return {"success": True, "message": "Attachment deleted successfully"}