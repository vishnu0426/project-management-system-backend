"""
Analytics and reporting models
"""
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Integer, Float, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from app.core.database import Base


class AnalyticsReport(Base):
    __tablename__ = "analytics_reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    report_type = Column(String(50), nullable=False)  # dashboard, project, user, organization, custom
    report_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    configuration = Column(JSON, nullable=False)  # Report configuration and filters
    chart_config = Column(JSON, nullable=True)  # Chart visualization settings
    schedule_config = Column(JSON, nullable=True)  # Automated report scheduling
    is_public = Column(Boolean, default=False, nullable=False)
    is_scheduled = Column(Boolean, default=False, nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    last_generated = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    organization = relationship("Organization")
    creator = relationship("User", foreign_keys=[created_by])
    executions = relationship("ReportExecution", back_populates="report", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<AnalyticsReport(id={self.id}, name={self.report_name}, type={self.report_type})>"


class ReportExecution(Base):
    __tablename__ = "report_executions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_id = Column(UUID(as_uuid=True), ForeignKey('analytics_reports.id', ondelete='CASCADE'), nullable=False)
    execution_type = Column(String(50), nullable=False)  # manual, scheduled, api
    status = Column(String(50), default='pending', nullable=False)  # pending, running, completed, failed
    result_data = Column(JSON, nullable=True)  # Generated report data
    file_path = Column(String(500), nullable=True)  # Path to exported file
    file_format = Column(String(20), nullable=True)  # pdf, excel, csv, json
    error_message = Column(Text, nullable=True)
    execution_time_ms = Column(Integer, nullable=True)  # Execution time in milliseconds
    record_count = Column(Integer, nullable=True)  # Number of records in result
    executed_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    report = relationship("AnalyticsReport", back_populates="executions")
    executor = relationship("User", foreign_keys=[executed_by])

    def __repr__(self):
        return f"<ReportExecution(id={self.id}, report_id={self.report_id}, status={self.status})>"


class DashboardWidget(Base):
    __tablename__ = "dashboard_widgets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=True)  # Null for org-wide widgets
    widget_type = Column(String(50), nullable=False)  # chart, metric, table, calendar, activity
    widget_name = Column(String(255), nullable=False)
    configuration = Column(JSON, nullable=False)  # Widget configuration
    position_x = Column(Integer, default=0, nullable=False)
    position_y = Column(Integer, default=0, nullable=False)
    width = Column(Integer, default=4, nullable=False)
    height = Column(Integer, default=3, nullable=False)
    is_visible = Column(Boolean, default=True, nullable=False)
    refresh_interval = Column(Integer, default=300, nullable=False)  # Refresh interval in seconds
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    organization = relationship("Organization")
    user = relationship("User", foreign_keys=[user_id])

    def __repr__(self):
        return f"<DashboardWidget(id={self.id}, type={self.widget_type}, name={self.widget_name})>"


class MetricSnapshot(Base):
    __tablename__ = "metric_snapshots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    metric_type = Column(String(50), nullable=False)  # user_count, project_count, task_completion, etc.
    metric_name = Column(String(255), nullable=False)
    metric_value = Column(Float, nullable=False)
    metric_unit = Column(String(50), nullable=True)  # count, percentage, hours, etc.
    dimensions = Column(JSON, nullable=True)  # Additional dimensions like project_id, user_id, etc.
    snapshot_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    organization = relationship("Organization")

    def __repr__(self):
        return f"<MetricSnapshot(id={self.id}, type={self.metric_type}, value={self.metric_value})>"


class DataExport(Base):
    __tablename__ = "data_exports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    export_type = Column(String(50), nullable=False)  # users, projects, tasks, analytics, full_backup
    export_format = Column(String(20), nullable=False)  # csv, excel, json, pdf
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=True)  # File size in bytes
    status = Column(String(50), default='pending', nullable=False)  # pending, processing, completed, failed
    filters = Column(JSON, nullable=True)  # Export filters and parameters
    record_count = Column(Integer, nullable=True)  # Number of records exported
    error_message = Column(Text, nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)  # When the export file expires
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    organization = relationship("Organization")
    creator = relationship("User", foreign_keys=[created_by])

    def __repr__(self):
        return f"<DataExport(id={self.id}, type={self.export_type}, status={self.status})>"


class PerformanceMetric(Base):
    __tablename__ = "performance_metrics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    project_id = Column(UUID(as_uuid=True), ForeignKey('projects.id', ondelete='CASCADE'), nullable=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=True)
    metric_category = Column(String(50), nullable=False)  # productivity, quality, efficiency, collaboration
    metric_name = Column(String(100), nullable=False)
    metric_value = Column(Float, nullable=False)
    target_value = Column(Float, nullable=True)
    measurement_period = Column(String(20), nullable=False)  # daily, weekly, monthly, quarterly
    measurement_date = Column(DateTime(timezone=True), nullable=False)
    metric_metadata = Column(JSON, nullable=True)  # Additional metric metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    organization = relationship("Organization")
    project = relationship("Project")
    user = relationship("User", foreign_keys=[user_id])

    def __repr__(self):
        return f"<PerformanceMetric(id={self.id}, category={self.metric_category}, name={self.metric_name})>"
