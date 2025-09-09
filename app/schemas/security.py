"""
Schemas for security and compliance features
"""
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID


class DataRetentionPolicyCreate(BaseModel):
    policy_name: str = Field(max_length=255)
    data_type: str = Field(max_length=100)
    retention_period_days: int = Field(gt=0)
    auto_delete: bool = False
    archive_before_delete: bool = True
    legal_basis: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None


class DataRetentionPolicyResponse(BaseModel):
    id: UUID
    organization_id: UUID
    policy_name: str
    data_type: str
    retention_period_days: int
    auto_delete: bool
    archive_before_delete: bool
    legal_basis: Optional[str] = None
    description: Optional[str] = None
    is_active: bool
    created_by: UUID
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class GDPRRequestCreate(BaseModel):
    request_type: str = Field(pattern="^(access|rectification|erasure|portability|restriction)$")
    requester_email: EmailStr
    requester_name: Optional[str] = None
    request_details: Optional[str] = None


class GDPRRequestResponse(BaseModel):
    id: UUID
    organization_id: UUID
    user_id: Optional[UUID] = None
    request_type: str
    status: str
    requester_email: str
    requester_name: Optional[str] = None
    request_details: Optional[str] = None
    verification_method: Optional[str] = None
    verification_completed: bool
    response_data: Optional[Dict[str, Any]] = None
    response_file_path: Optional[str] = None
    rejection_reason: Optional[str] = None
    processed_by: Optional[UUID] = None
    due_date: datetime
    created_at: datetime
    completed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class SecurityEventResponse(BaseModel):
    id: UUID
    organization_id: Optional[UUID] = None
    user_id: Optional[UUID] = None
    event_type: str
    severity: str
    event_source: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    event_data: Optional[Dict[str, Any]] = None
    risk_score: Optional[int] = None
    is_resolved: bool
    resolved_by: Optional[UUID] = None
    resolution_notes: Optional[str] = None
    created_at: datetime
    resolved_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class SecurityAlertResponse(BaseModel):
    id: UUID
    organization_id: Optional[UUID] = None
    alert_type: str
    severity: str
    title: str
    description: str
    affected_resources: Optional[List[Dict[str, Any]]] = None
    detection_method: str
    alert_source: str
    status: str
    assigned_to: Optional[UUID] = None
    escalation_level: int
    response_actions: Optional[List[Dict[str, Any]]] = None
    resolution_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class BackupRecordResponse(BaseModel):
    id: UUID
    organization_id: Optional[UUID] = None
    backup_type: str
    backup_scope: str
    file_path: str
    file_size: Optional[int] = None
    compression_type: Optional[str] = None
    encryption_enabled: bool
    checksum: Optional[str] = None
    status: str
    error_message: Optional[str] = None
    retention_until: Optional[datetime] = None
    created_by: Optional[UUID] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class ComplianceAuditResponse(BaseModel):
    id: UUID
    organization_id: UUID
    audit_type: str
    audit_scope: str
    status: str
    compliance_framework: str
    auditor_name: Optional[str] = None
    auditor_organization: Optional[str] = None
    findings: Optional[Dict[str, Any]] = None
    compliance_score: Optional[int] = None
    report_file_path: Optional[str] = None
    remediation_plan: Optional[Dict[str, Any]] = None
    next_audit_date: Optional[datetime] = None
    created_by: UUID
    created_at: datetime
    completed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class ConsentRecordCreate(BaseModel):
    consent_type: str = Field(max_length=100)
    consent_given: bool
    consent_method: str = Field(pattern="^(explicit|implicit|opt_in|opt_out)$")
    legal_basis: Optional[str] = Field(None, max_length=100)
    purpose_description: str
    data_categories: Optional[List[str]] = None
    retention_period: Optional[str] = None
    third_party_sharing: bool = False
    consent_version: str = Field(max_length=20)
    expires_at: Optional[datetime] = None


class ConsentRecordResponse(BaseModel):
    id: UUID
    user_id: UUID
    organization_id: UUID
    consent_type: str
    consent_given: bool
    consent_method: str
    legal_basis: Optional[str] = None
    purpose_description: str
    data_categories: Optional[List[str]] = None
    retention_period: Optional[str] = None
    third_party_sharing: bool
    withdrawal_method: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    consent_version: str
    expires_at: Optional[datetime] = None
    withdrawn_at: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class SecurityDashboard(BaseModel):
    organization_id: UUID
    security_score: int  # 0-100 overall security score
    active_alerts: int
    critical_alerts: int
    recent_events: List[SecurityEventResponse]
    compliance_status: Dict[str, Any]
    backup_status: Dict[str, Any]
    gdpr_requests_pending: int
    last_security_audit: Optional[datetime] = None


class ComplianceReport(BaseModel):
    organization_id: UUID
    report_type: str
    compliance_framework: str
    overall_score: int
    categories: List[Dict[str, Any]]
    recommendations: List[Dict[str, Any]]
    action_items: List[Dict[str, Any]]
    generated_at: datetime


class SecurityIncident(BaseModel):
    incident_id: UUID
    title: str
    description: str
    severity: str
    status: str
    affected_systems: List[str]
    timeline: List[Dict[str, Any]]
    response_team: List[UUID]
    lessons_learned: Optional[str] = None
    created_at: datetime
    resolved_at: Optional[datetime] = None


class RiskAssessment(BaseModel):
    organization_id: UUID
    assessment_date: datetime
    risk_categories: List[Dict[str, Any]]
    overall_risk_score: int
    high_risk_areas: List[str]
    mitigation_strategies: List[Dict[str, Any]]
    next_assessment_date: datetime


class SecurityMetrics(BaseModel):
    organization_id: UUID
    period: str  # daily, weekly, monthly
    metrics: Dict[str, Any]
    trends: Dict[str, Any]
    benchmarks: Dict[str, Any]
    generated_at: datetime
