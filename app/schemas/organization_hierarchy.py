"""
Schemas for organization hierarchy and collaboration features
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID


class OrganizationBase(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    organization_type: str
    
    class Config:
        from_attributes = True


class OrganizationHierarchy(BaseModel):
    organization: OrganizationBase
    parent: Optional[OrganizationBase] = None
    children: List[OrganizationBase] = []
    organization_type: str
    
    class Config:
        from_attributes = True


class OrganizationCollaborationCreate(BaseModel):
    partner_organization_id: UUID
    collaboration_type: str = Field(default="project_sharing", pattern="^(project_sharing|resource_sharing|full_access)$")
    permissions: Optional[List[str]] = None
    expires_at: Optional[datetime] = None


class OrganizationCollaborationUpdate(BaseModel):
    status: Optional[str] = Field(None, pattern="^(pending|active|suspended|terminated)$")
    permissions: Optional[List[str]] = None
    expires_at: Optional[datetime] = None


class OrganizationCollaborationResponse(BaseModel):
    id: UUID
    organization_id: UUID
    partner_organization_id: UUID
    collaboration_type: str
    status: str
    permissions: Optional[List[str]] = None
    created_by: UUID
    approved_by: Optional[UUID] = None
    created_at: datetime
    approved_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class BulkUserOperationCreate(BaseModel):
    operation_type: str = Field(pattern="^(import|export|bulk_invite|bulk_update|bulk_delete)$")
    file_name: Optional[str] = None
    operation_data: Optional[Dict[str, Any]] = None


class BulkUserOperationResponse(BaseModel):
    id: UUID
    organization_id: UUID
    operation_type: str
    status: str
    file_path: Optional[str] = None
    file_name: Optional[str] = None
    total_records: int
    processed_records: int
    successful_records: int
    failed_records: int
    error_details: Optional[Dict[str, Any]] = None
    result_data: Optional[Dict[str, Any]] = None
    created_by: UUID
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class BulkOperationLogResponse(BaseModel):
    id: UUID
    bulk_operation_id: UUID
    record_index: int
    record_data: Optional[Dict[str, Any]] = None
    operation_result: str
    error_message: Optional[str] = None
    created_user_id: Optional[UUID] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class OrganizationTemplateCreate(BaseModel):
    name: str = Field(max_length=255)
    description: Optional[str] = None
    template_type: str = Field(pattern="^(startup|agency|enterprise|custom)$")
    industry: Optional[str] = None
    configuration: Dict[str, Any]
    default_roles: Optional[List[Dict[str, Any]]] = None
    default_projects: Optional[List[Dict[str, Any]]] = None
    default_workflows: Optional[Dict[str, Any]] = None
    is_public: str = Field(default="private", pattern="^(public|private|organization)$")


class OrganizationTemplateResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    template_type: str
    industry: Optional[str] = None
    configuration: Dict[str, Any]
    default_roles: Optional[List[Dict[str, Any]]] = None
    default_projects: Optional[List[Dict[str, Any]]] = None
    default_workflows: Optional[Dict[str, Any]] = None
    is_public: str
    created_by: UUID
    organization_id: Optional[UUID] = None
    usage_count: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class BulkUserImportData(BaseModel):
    email: str
    first_name: str
    last_name: str
    role: str = Field(default="member", pattern="^(viewer|member|admin|owner)$")
    department: Optional[str] = None
    job_title: Optional[str] = None
    send_invitation: bool = True


class BulkUserExportFilter(BaseModel):
    roles: Optional[List[str]] = None
    departments: Optional[List[str]] = None
    include_inactive: bool = False
    date_range: Optional[Dict[str, datetime]] = None


class OrganizationAnalytics(BaseModel):
    total_members: int
    active_members: int
    total_projects: int
    active_projects: int
    total_tasks: int
    completed_tasks: int
    collaboration_count: int
    hierarchy_depth: int
    member_growth: List[Dict[str, Any]]
    project_completion_rate: float
    average_task_completion_time: Optional[float] = None
    
    class Config:
        from_attributes = True
