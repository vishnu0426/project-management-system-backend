"""
File upload endpoints with enhanced security validation
"""
import os
import uuid
import mimetypes
from typing import List, Dict
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
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
from app.config import settings

router = APIRouter()


# File validation using Python's built-in mimetypes module
# No external dependencies required


def validate_file(file: UploadFile) -> None:
    """Enhanced file validation with MIME type checking using built-in mimetypes"""

    # Check if file exists and has content
    if not file.filename:
        raise ValidationError("No file provided")

    # Check file size (return 413 for oversized files)
    if file.size and file.size > settings.max_file_size:
        raise HTTPException(
            status_code=413,
            detail=f"File size ({file.size} bytes) exceeds maximum allowed size of {settings.max_file_size} bytes"
        )

    # Check file extension
    file_extension = file.filename.split('.')[-1].lower() if '.' in file.filename else ''
    if file_extension not in settings.allowed_file_types:
        raise ValidationError(
            f"File type '{file_extension}' not allowed. Allowed types: {', '.join(settings.allowed_file_types)}"
        )

    # Validate MIME type matches extension using built-in mimetypes
    if file.content_type:
        # Get expected MIME type for the file extension
        expected_mime_type, _ = mimetypes.guess_type(file.filename)

        # Check if the provided content type matches expected type
        if expected_mime_type and file.content_type != expected_mime_type:
            # Allow some common variations
            mime_variations = {
                'image/jpg': 'image/jpeg',
                'image/jpeg': 'image/jpg',
                'application/x-pdf': 'application/pdf'
            }

            expected_alt = mime_variations.get(expected_mime_type)
            provided_alt = mime_variations.get(file.content_type)

            if (file.content_type != expected_alt and
                provided_alt != expected_mime_type and
                provided_alt != expected_alt):
                raise ValidationError(
                    f"MIME type '{file.content_type}' does not match file extension '{file_extension}'. "
                    f"Expected: {expected_mime_type}"
                )

    # Additional security: Check for dangerous filenames
    dangerous_patterns = ['..', '/', '\\', '<', '>', ':', '"', '|', '?', '*']
    if any(pattern in file.filename for pattern in dangerous_patterns):
        raise ValidationError("Filename contains dangerous characters")


def generate_filename(original_filename: str) -> str:
    """Generate unique filename"""
    file_extension = original_filename.split('.')[-1] if '.' in original_filename else ''
    unique_id = str(uuid.uuid4())
    return f"{unique_id}.{file_extension}" if file_extension else unique_id


async def save_file(file: UploadFile, directory: str) -> str:
    """Save file to storage and return URL"""
    # Create directory if it doesn't exist
    os.makedirs(directory, exist_ok=True)
    
    # Generate unique filename
    filename = generate_filename(file.filename)
    file_path = os.path.join(directory, filename)
    
    # Save file
    with open(file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)
    
    # Return relative URL
    return f"/uploads/{os.path.relpath(file_path, 'uploads')}"


@router.post("/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Upload user avatar"""
    # Validate file
    validate_file(file)
    
    # Additional validation for avatars
    if not file.content_type.startswith('image/'):
        raise ValidationError("Avatar must be an image file")
    
    # Save file
    directory = f"uploads/avatars/{current_user.id}"
    file_url = await save_file(file, directory)
    
    # Update user avatar URL
    current_user.avatar_url = file_url
    await db.commit()
    
    return {
        "success": True,
        "data": {
            "avatar_url": file_url
        },
        "message": "Avatar uploaded successfully"
    }


@router.post("/organization-logo")
async def upload_organization_logo(
    org_id: str,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Upload organization logo"""
    # Validate file
    validate_file(file)
    
    # Additional validation for logos
    if not file.content_type.startswith('image/'):
        raise ValidationError("Logo must be an image file")
    
    # TODO: Check if user has permission to upload logo for this organization
    
    # Save file
    directory = f"uploads/organizations/{org_id}"
    file_url = await save_file(file, directory)
    
    return {
        "success": True,
        "data": {
            "logo_url": file_url
        },
        "message": "Logo uploaded successfully"
    }


@router.post("/card-attachment")
async def upload_card_attachment(
    card_id: str,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Upload card attachment"""
    # Validate file
    validate_file(file)
    
    # Check if card exists and user has access
    card_result = await db.execute(
        select(Card).where(Card.id == card_id)
    )
    card = card_result.scalar_one_or_none()
    if not card:
        raise ResourceNotFoundError("Card not found")
    
    # TODO: Check if user has permission to add attachments to this card
    
    # Save file
    directory = f"uploads/attachments/{card_id}"
    file_url = await save_file(file, directory)
    
    # Create attachment record
    attachment = Attachment(
        card_id=card_id,
        filename=generate_filename(file.filename),
        original_name=file.filename,
        file_size=file.size,
        mime_type=file.content_type,
        file_url=file_url,
        uploaded_by=current_user.id
    )
    
    db.add(attachment)
    await db.commit()
    await db.refresh(attachment)
    
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
                "uploaded_at": attachment.uploaded_at.isoformat()
            }
        },
        "message": "Attachment uploaded successfully"
    }


@router.delete("/{file_id}")
async def delete_file(
    file_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete uploaded file"""
    # Check if file is an attachment
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

    if attachment:
        # Check if user has permission to delete this attachment
        if attachment.card:
            # Check organization membership
            org_member_result = await db.execute(
                select(OrganizationMember).where(
                    OrganizationMember.organization_id == attachment.card.column.board.project.organization_id,
                    OrganizationMember.user_id == current_user.id
                )
            )
            org_member = org_member_result.scalar_one_or_none()
            if not org_member:
                raise InsufficientPermissionsError("Access denied")

            # Check if project data is protected
            project = attachment.card.column.board.project
            if project.data_protected:
                # Only owners can delete attachments from protected projects
                if org_member.role != 'owner':
                    raise HTTPException(
                        status_code=403,
                        detail=f"Cannot delete attachment: Project data is protected. Reason: {project.protection_reason or 'Data protection enabled'}"
                    )

                # Even owners get a warning about protected data
                if project.sign_off_requested and not project.sign_off_approved:
                    raise HTTPException(
                        status_code=403,
                        detail="Cannot delete attachment: Project is pending sign-off approval. Complete the sign-off process first."
                    )

        # Delete file from storage
        try:
            file_path = f"uploads{attachment.file_url.replace('/uploads', '')}"
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception:
            pass  # File might already be deleted

        # Delete attachment record
        await db.delete(attachment)
        await db.commit()

        return {"success": True, "message": "Attachment deleted successfully"}

    raise ResourceNotFoundError("File not found")


@router.get("/{file_id}/download")
async def download_file(
    file_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Download file"""
    # Check if file is an attachment
    attachment_result = await db.execute(
        select(Attachment).where(Attachment.id == file_id)
    )
    attachment = attachment_result.scalar_one_or_none()
    
    if attachment:
        # TODO: Check if user has permission to download this attachment
        # TODO: Return file download response
        return {
            "success": True,
            "data": {
                "download_url": attachment.file_url
            }
        }
    
    raise ResourceNotFoundError("File not found")
