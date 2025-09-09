"""
Bulk operations API endpoints for user management
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
import csv
import io
import json
from datetime import datetime

from app.core.database import get_db
from app.core.deps import get_current_active_user
from app.models.user import User
from app.models.organization import Organization, OrganizationMember
from app.models.bulk_operations import BulkUserOperation, BulkOperationLog
from app.schemas.organization_hierarchy import (
    BulkUserOperationCreate,
    BulkUserOperationResponse,
    BulkOperationLogResponse,
    BulkUserImportData,
    BulkUserExportFilter
)
from app.services.email_service import send_invitation_email

router = APIRouter()


async def process_bulk_user_import(
    operation_id: UUID,
    file_content: str,
    organization_id: UUID,
    db: Session
):
    """Background task to process bulk user import"""
    operation = db.query(BulkUserOperation).filter(BulkUserOperation.id == operation_id).first()
    if not operation:
        return
    
    try:
        operation.status = 'processing'
        operation.started_at = datetime.utcnow()
        db.commit()
        
        # Parse CSV content
        csv_reader = csv.DictReader(io.StringIO(file_content))
        rows = list(csv_reader)
        operation.total_records = len(rows)
        db.commit()
        
        for index, row in enumerate(rows):
            try:
                # Validate required fields
                if not row.get('email') or not row.get('first_name') or not row.get('last_name'):
                    raise ValueError("Missing required fields: email, first_name, last_name")
                
                # Check if user already exists
                existing_user = db.query(User).filter(User.email == row['email']).first()
                if existing_user:
                    # Check if already member of organization
                    existing_member = db.query(OrganizationMember).filter(
                        OrganizationMember.organization_id == organization_id,
                        OrganizationMember.user_id == existing_user.id
                    ).first()
                    
                    if existing_member:
                        # Log as skipped
                        log_entry = BulkOperationLog(
                            bulk_operation_id=operation_id,
                            record_index=index + 1,
                            record_data=row,
                            operation_result='skipped',
                            error_message='User already member of organization'
                        )
                        db.add(log_entry)
                        continue
                    else:
                        # Add existing user to organization
                        member = OrganizationMember(
                            organization_id=organization_id,
                            user_id=existing_user.id,
                            role=row.get('role', 'member'),
                            invited_by=operation.created_by
                        )
                        db.add(member)
                        
                        # Send invitation email if requested
                        if row.get('send_invitation', 'true').lower() == 'true':
                            await send_invitation_email(existing_user.email, organization_id, db)
                        
                        log_entry = BulkOperationLog(
                            bulk_operation_id=operation_id,
                            record_index=index + 1,
                            record_data=row,
                            operation_result='success',
                            created_user_id=existing_user.id
                        )
                        db.add(log_entry)
                        operation.successful_records += 1
                else:
                    # Create new user
                    new_user = User(
                        email=row['email'],
                        first_name=row['first_name'],
                        last_name=row['last_name'],
                        is_active=True,
                        email_verified=False
                    )
                    db.add(new_user)
                    db.flush()  # Get the user ID
                    
                    # Add to organization
                    member = OrganizationMember(
                        organization_id=organization_id,
                        user_id=new_user.id,
                        role=row.get('role', 'member'),
                        invited_by=operation.created_by
                    )
                    db.add(member)
                    
                    # Send invitation email
                    if row.get('send_invitation', 'true').lower() == 'true':
                        await send_invitation_email(new_user.email, organization_id, db)
                    
                    log_entry = BulkOperationLog(
                        bulk_operation_id=operation_id,
                        record_index=index + 1,
                        record_data=row,
                        operation_result='success',
                        created_user_id=new_user.id
                    )
                    db.add(log_entry)
                    operation.successful_records += 1
                
                operation.processed_records += 1
                
            except Exception as e:
                # Log error
                log_entry = BulkOperationLog(
                    bulk_operation_id=operation_id,
                    record_index=index + 1,
                    record_data=row,
                    operation_result='failed',
                    error_message=str(e)
                )
                db.add(log_entry)
                operation.failed_records += 1
                operation.processed_records += 1
            
            db.commit()
        
        operation.status = 'completed'
        operation.completed_at = datetime.utcnow()
        db.commit()
        
    except Exception as e:
        operation.status = 'failed'
        operation.error_details = {'error': str(e)}
        operation.completed_at = datetime.utcnow()
        db.commit()


@router.post("/organizations/{organization_id}/bulk-operations", response_model=BulkUserOperationResponse)
async def create_bulk_operation(
    organization_id: UUID,
    operation_data: BulkUserOperationCreate,
    background_tasks: BackgroundTasks,
    file: Optional[UploadFile] = File(None),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new bulk operation"""
    # Check if user is owner/admin of the organization
    member = db.query(OrganizationMember).filter(
        OrganizationMember.organization_id == organization_id,
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.role.in_(['owner', 'admin'])
    ).first()
    
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owners and admins can perform bulk operations"
        )
    
    # Create bulk operation record
    operation = BulkUserOperation(
        organization_id=organization_id,
        operation_type=operation_data.operation_type,
        file_name=operation_data.file_name,
        created_by=current_user.id
    )
    
    db.add(operation)
    db.commit()
    db.refresh(operation)
    
    # Handle file upload for import operations
    if operation_data.operation_type == 'import' and file:
        if not file.filename.endswith('.csv'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only CSV files are supported for import"
            )
        
        # Read file content
        content = await file.read()
        file_content = content.decode('utf-8')
        
        # Start background processing
        background_tasks.add_task(
            process_bulk_user_import,
            operation.id,
            file_content,
            organization_id,
            db
        )
    
    return operation


@router.get("/organizations/{organization_id}/bulk-operations", response_model=List[BulkUserOperationResponse])
async def get_bulk_operations(
    organization_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all bulk operations for an organization"""
    # Check if user has access to this organization
    member = db.query(OrganizationMember).filter(
        OrganizationMember.organization_id == organization_id,
        OrganizationMember.user_id == current_user.id
    ).first()
    
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to organization"
        )
    
    operations = db.query(BulkUserOperation).filter(
        BulkUserOperation.organization_id == organization_id
    ).order_by(BulkUserOperation.created_at.desc()).all()
    
    return operations


@router.get("/organizations/{organization_id}/bulk-operations/{operation_id}", response_model=BulkUserOperationResponse)
async def get_bulk_operation(
    organization_id: UUID,
    operation_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get specific bulk operation details"""
    # Check if user has access to this organization
    member = db.query(OrganizationMember).filter(
        OrganizationMember.organization_id == organization_id,
        OrganizationMember.user_id == current_user.id
    ).first()
    
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to organization"
        )
    
    operation = db.query(BulkUserOperation).filter(
        BulkUserOperation.id == operation_id,
        BulkUserOperation.organization_id == organization_id
    ).first()
    
    if not operation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bulk operation not found"
        )
    
    return operation


@router.get("/organizations/{organization_id}/bulk-operations/{operation_id}/logs", response_model=List[BulkOperationLogResponse])
async def get_bulk_operation_logs(
    organization_id: UUID,
    operation_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get logs for a specific bulk operation"""
    # Check if user has access to this organization
    member = db.query(OrganizationMember).filter(
        OrganizationMember.organization_id == organization_id,
        OrganizationMember.user_id == current_user.id
    ).first()
    
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to organization"
        )
    
    # Verify operation exists and belongs to organization
    operation = db.query(BulkUserOperation).filter(
        BulkUserOperation.id == operation_id,
        BulkUserOperation.organization_id == organization_id
    ).first()
    
    if not operation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bulk operation not found"
        )
    
    logs = db.query(BulkOperationLog).filter(
        BulkOperationLog.bulk_operation_id == operation_id
    ).order_by(BulkOperationLog.record_index).all()
    
    return logs


@router.delete("/organizations/{organization_id}/bulk-operations/{operation_id}")
async def cancel_bulk_operation(
    organization_id: UUID,
    operation_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Cancel a pending or processing bulk operation"""
    # Check if user is owner/admin of the organization
    member = db.query(OrganizationMember).filter(
        OrganizationMember.organization_id == organization_id,
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.role.in_(['owner', 'admin'])
    ).first()
    
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owners and admins can cancel bulk operations"
        )
    
    operation = db.query(BulkUserOperation).filter(
        BulkUserOperation.id == operation_id,
        BulkUserOperation.organization_id == organization_id
    ).first()
    
    if not operation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bulk operation not found"
        )
    
    if operation.status not in ['pending', 'processing']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only cancel pending or processing operations"
        )
    
    operation.status = 'cancelled'
    operation.completed_at = datetime.utcnow()
    db.commit()
    
    return {"message": "Bulk operation cancelled successfully"}
