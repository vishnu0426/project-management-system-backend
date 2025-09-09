"""
Schemas for analytics and reporting features
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from uuid import UUID


class AnalyticsReportCreate(BaseModel):
    report_type: str = Field(pattern="^(dashboard|project|user|organization|custom)$")
    report_name: str = Field(max_length=255)
    description: Optional[str] = None
    configuration: Dict[str, Any]
    chart_config: Optional[Dict[str, Any]] = None
    schedule_config: Optional[Dict[str, Any]] = None
    is_public: bool = False
    is_scheduled: bool = False


class AnalyticsReportResponse(BaseModel):
    id: UUID
    organization_id: UUID
    report_type: str
    report_name: str
    description: Optional[str] = None
    configuration: Dict[str, Any]
    chart_config: Optional[Dict[str, Any]] = None
    schedule_config: Optional[Dict[str, Any]] = None
    is_public: bool
    is_scheduled: bool
    created_by: UUID
    created_at: datetime
    updated_at: datetime
    last_generated: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class DashboardWidgetCreate(BaseModel):
    widget_type: str = Field(pattern="^(chart|metric|table|calendar|activity)$")
    widget_name: str = Field(max_length=255)
    configuration: Dict[str, Any]
    position_x: int = Field(ge=0)
    position_y: int = Field(ge=0)
    width: int = Field(ge=1, le=12)
    height: int = Field(ge=1, le=12)
    refresh_interval: int = Field(ge=30, default=300)  # Minimum 30 seconds


class DashboardWidgetResponse(BaseModel):
    id: UUID
    organization_id: UUID
    user_id: Optional[UUID] = None
    widget_type: str
    widget_name: str
    configuration: Dict[str, Any]
    position_x: int
    position_y: int
    width: int
    height: int
    is_visible: bool
    refresh_interval: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class DataExportCreate(BaseModel):
    export_type: str = Field(pattern="^(users|projects|tasks|analytics|full_backup)$")
    export_format: str = Field(pattern="^(csv|excel|json|pdf)$")
    filters: Optional[Dict[str, Any]] = None


class DataExportResponse(BaseModel):
    id: UUID
    organization_id: UUID
    export_type: str
    export_format: str
    file_name: str
    file_path: str
    file_size: Optional[int] = None
    status: str
    filters: Optional[Dict[str, Any]] = None
    record_count: Optional[int] = None
    error_message: Optional[str] = None
    expires_at: Optional[datetime] = None
    created_by: UUID
    created_at: datetime
    completed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class OrganizationAnalytics(BaseModel):
    total_members: int
    active_members: int
    total_projects: int
    active_projects: int
    total_tasks: int
    completed_tasks: int
    completion_rate: float
    project_completion_rate: float
    member_growth: List[Dict[str, Any]]
    average_task_completion_time: Optional[float] = None


class ProjectAnalytics(BaseModel):
    project_id: UUID
    total_tasks: int
    completed_tasks: int
    progress_percentage: float
    overdue_tasks: int
    task_by_status: Dict[str, int]
    task_by_priority: Dict[str, int]
    task_by_assignee: List[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime


class UserAnalytics(BaseModel):
    user_id: UUID
    total_tasks_assigned: int
    completed_tasks: int
    overdue_tasks: int
    completion_rate: float
    average_completion_time: Optional[float] = None
    productivity_score: float
    recent_activity: List[Dict[str, Any]]


class ChartData(BaseModel):
    chart_type: str = Field(pattern="^(line|bar|pie|doughnut|area|scatter)$")
    title: str
    labels: List[str]
    datasets: List[Dict[str, Any]]
    options: Optional[Dict[str, Any]] = None


class MetricCard(BaseModel):
    title: str
    value: Union[int, float, str]
    unit: Optional[str] = None
    change: Optional[float] = None  # Percentage change from previous period
    trend: Optional[str] = None  # up, down, stable
    color: Optional[str] = None


class AnalyticsDashboard(BaseModel):
    organization_id: UUID
    metrics: List[MetricCard]
    charts: List[ChartData]
    widgets: List[DashboardWidgetResponse]
    last_updated: datetime


class ReportExecutionResponse(BaseModel):
    id: UUID
    report_id: UUID
    execution_type: str
    status: str
    result_data: Optional[Dict[str, Any]] = None
    file_path: Optional[str] = None
    file_format: Optional[str] = None
    error_message: Optional[str] = None
    execution_time_ms: Optional[int] = None
    record_count: Optional[int] = None
    executed_by: Optional[UUID] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class PerformanceMetricResponse(BaseModel):
    id: UUID
    organization_id: UUID
    project_id: Optional[UUID] = None
    user_id: Optional[UUID] = None
    metric_category: str
    metric_name: str
    metric_value: float
    target_value: Optional[float] = None
    measurement_period: str
    measurement_date: datetime
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class AnalyticsFilter(BaseModel):
    date_range: Optional[str] = Field(None, pattern="^(7d|30d|90d|1y|all)$")
    project_ids: Optional[List[UUID]] = None
    user_ids: Optional[List[UUID]] = None
    status_filter: Optional[List[str]] = None
    priority_filter: Optional[List[str]] = None
    custom_filters: Optional[Dict[str, Any]] = None


class BulkAnalyticsRequest(BaseModel):
    metrics: List[str]  # List of metric names to calculate
    filters: Optional[AnalyticsFilter] = None
    group_by: Optional[List[str]] = None  # Group results by these fields
    aggregation: Optional[str] = Field("sum", pattern="^(sum|avg|count|min|max)$")


class TimeSeriesData(BaseModel):
    metric_name: str
    data_points: List[Dict[str, Any]]  # [{date: "2024-01-01", value: 100}, ...]
    period: str  # daily, weekly, monthly
    total: Optional[float] = None
    average: Optional[float] = None


class ComparisonAnalytics(BaseModel):
    current_period: Dict[str, Any]
    previous_period: Dict[str, Any]
    change_percentage: float
    trend: str  # improving, declining, stable
