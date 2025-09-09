"""
Security monitoring and compliance service
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from app.models.security import SecurityEvent, SecurityAlert, BackupRecord, ConsentRecord
from app.models.user import User
from app.models.organization import Organization, OrganizationMember
from app.models.activity_log import ActivityLog
from app.core.database import get_db

logger = logging.getLogger(__name__)


class SecurityMonitoringService:
    """Service for security monitoring and threat detection"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def log_security_event(
        self,
        event_type: str,
        severity: str,
        event_source: str,
        organization_id: Optional[str] = None,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        event_data: Optional[Dict[str, Any]] = None
    ) -> SecurityEvent:
        """Log a security event"""
        try:
            # Calculate risk score based on event type and severity
            risk_score = self._calculate_risk_score(event_type, severity, event_data)
            
            event = SecurityEvent(
                organization_id=organization_id,
                user_id=user_id,
                event_type=event_type,
                severity=severity,
                event_source=event_source,
                ip_address=ip_address,
                user_agent=user_agent,
                event_data=event_data,
                risk_score=risk_score
            )
            
            self.db.add(event)
            self.db.commit()
            
            # Check if this event should trigger an alert
            if risk_score >= 70 or severity in ['high', 'critical']:
                self._create_security_alert(event)
            
            logger.info(f"Security event logged: {event_type} (severity: {severity})")
            return event
            
        except Exception as e:
            logger.error(f"Error logging security event: {e}")
            self.db.rollback()
            raise
    
    def _calculate_risk_score(
        self, 
        event_type: str, 
        severity: str, 
        event_data: Optional[Dict[str, Any]] = None
    ) -> int:
        """Calculate risk score for security event"""
        base_scores = {
            'login_failure': 20,
            'suspicious_activity': 50,
            'data_breach': 90,
            'unauthorized_access': 70,
            'brute_force_attempt': 60,
            'privilege_escalation': 80,
            'data_export': 40,
            'unusual_location': 30,
            'multiple_failed_logins': 50
        }
        
        severity_multipliers = {
            'low': 0.5,
            'medium': 1.0,
            'high': 1.5,
            'critical': 2.0
        }
        
        base_score = base_scores.get(event_type, 30)
        multiplier = severity_multipliers.get(severity, 1.0)
        
        # Additional factors from event data
        additional_risk = 0
        if event_data:
            if event_data.get('repeated_attempts', 0) > 5:
                additional_risk += 20
            if event_data.get('from_unknown_location'):
                additional_risk += 15
            if event_data.get('admin_account_targeted'):
                additional_risk += 25
        
        final_score = min(100, int((base_score * multiplier) + additional_risk))
        return final_score
    
    def _create_security_alert(self, event: SecurityEvent) -> SecurityAlert:
        """Create security alert from high-risk event"""
        try:
            alert_title = self._generate_alert_title(event.event_type, event.severity)
            alert_description = self._generate_alert_description(event)
            
            alert = SecurityAlert(
                organization_id=event.organization_id,
                alert_type=event.event_type,
                severity=event.severity,
                title=alert_title,
                description=alert_description,
                affected_resources=[{
                    'type': 'security_event',
                    'id': str(event.id),
                    'user_id': str(event.user_id) if event.user_id else None
                }],
                detection_method='automated',
                alert_source='security_monitoring',
                escalation_level=self._get_escalation_level(event.severity)
            )
            
            self.db.add(alert)
            self.db.commit()
            
            logger.warning(f"Security alert created: {alert_title}")
            return alert
            
        except Exception as e:
            logger.error(f"Error creating security alert: {e}")
            self.db.rollback()
            raise
    
    def _generate_alert_title(self, event_type: str, severity: str) -> str:
        """Generate alert title based on event type"""
        titles = {
            'login_failure': f"{severity.title()} Login Failure Detected",
            'suspicious_activity': f"{severity.title()} Suspicious Activity Detected",
            'data_breach': f"{severity.title()} Data Breach Alert",
            'unauthorized_access': f"{severity.title()} Unauthorized Access Attempt",
            'brute_force_attempt': f"{severity.title()} Brute Force Attack Detected",
            'privilege_escalation': f"{severity.title()} Privilege Escalation Attempt"
        }
        return titles.get(event_type, f"{severity.title()} Security Event: {event_type}")
    
    def _generate_alert_description(self, event: SecurityEvent) -> str:
        """Generate detailed alert description"""
        description = f"Security event of type '{event.event_type}' detected "
        
        if event.user_id:
            description += f"for user {event.user_id} "
        
        if event.ip_address:
            description += f"from IP address {event.ip_address} "
        
        description += f"at {event.created_at}. "
        description += f"Risk score: {event.risk_score}/100. "
        
        if event.event_data:
            description += f"Additional details: {event.event_data}"
        
        return description
    
    def _get_escalation_level(self, severity: str) -> int:
        """Get escalation level based on severity"""
        levels = {
            'low': 1,
            'medium': 2,
            'high': 3,
            'critical': 4
        }
        return levels.get(severity, 2)
    
    def detect_anomalies(self, organization_id: str) -> List[Dict[str, Any]]:
        """Detect security anomalies for organization"""
        anomalies = []
        
        try:
            # Check for unusual login patterns
            login_anomalies = self._detect_login_anomalies(organization_id)
            anomalies.extend(login_anomalies)
            
            # Check for data access anomalies
            access_anomalies = self._detect_access_anomalies(organization_id)
            anomalies.extend(access_anomalies)
            
            # Check for privilege escalation attempts
            privilege_anomalies = self._detect_privilege_anomalies(organization_id)
            anomalies.extend(privilege_anomalies)
            
            return anomalies
            
        except Exception as e:
            logger.error(f"Error detecting anomalies: {e}")
            return []
    
    def _detect_login_anomalies(self, organization_id: str) -> List[Dict[str, Any]]:
        """Detect unusual login patterns"""
        anomalies = []
        
        # Check for multiple failed logins
        failed_logins = self.db.query(SecurityEvent).filter(
            SecurityEvent.organization_id == organization_id,
            SecurityEvent.event_type == 'login_failure',
            SecurityEvent.created_at >= datetime.utcnow() - timedelta(hours=1)
        ).count()
        
        if failed_logins > 10:
            anomalies.append({
                'type': 'multiple_failed_logins',
                'severity': 'medium',
                'description': f'{failed_logins} failed login attempts in the last hour',
                'count': failed_logins
            })
        
        # Check for logins from unusual locations
        # This would require IP geolocation data
        
        return anomalies
    
    def _detect_access_anomalies(self, organization_id: str) -> List[Dict[str, Any]]:
        """Detect unusual data access patterns"""
        anomalies = []
        
        # Check for unusual data export activity
        recent_exports = self.db.query(ActivityLog).filter(
            ActivityLog.organization_id == organization_id,
            ActivityLog.action.like('%export%'),
            ActivityLog.created_at >= datetime.utcnow() - timedelta(hours=24)
        ).count()
        
        if recent_exports > 5:
            anomalies.append({
                'type': 'unusual_export_activity',
                'severity': 'medium',
                'description': f'{recent_exports} data exports in the last 24 hours',
                'count': recent_exports
            })
        
        return anomalies
    
    def _detect_privilege_anomalies(self, organization_id: str) -> List[Dict[str, Any]]:
        """Detect privilege escalation attempts"""
        anomalies = []
        
        # Check for role changes
        role_changes = self.db.query(ActivityLog).filter(
            ActivityLog.organization_id == organization_id,
            ActivityLog.action.like('%role%'),
            ActivityLog.created_at >= datetime.utcnow() - timedelta(hours=24)
        ).count()
        
        if role_changes > 3:
            anomalies.append({
                'type': 'multiple_role_changes',
                'severity': 'high',
                'description': f'{role_changes} role changes in the last 24 hours',
                'count': role_changes
            })
        
        return anomalies
    
    def generate_security_report(self, organization_id: str) -> Dict[str, Any]:
        """Generate comprehensive security report"""
        try:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=30)
            
            # Get security events summary
            events_summary = self.db.query(
                SecurityEvent.severity,
                func.count(SecurityEvent.id).label('count')
            ).filter(
                SecurityEvent.organization_id == organization_id,
                SecurityEvent.created_at >= start_date
            ).group_by(SecurityEvent.severity).all()
            
            # Get active alerts
            active_alerts = self.db.query(SecurityAlert).filter(
                SecurityAlert.organization_id == organization_id,
                SecurityAlert.status.in_(['open', 'investigating'])
            ).count()
            
            # Get backup status
            latest_backup = self.db.query(BackupRecord).filter(
                BackupRecord.organization_id == organization_id,
                BackupRecord.status == 'completed'
            ).order_by(BackupRecord.completed_at.desc()).first()
            
            # Calculate security score
            security_score = self._calculate_security_score(organization_id)
            
            return {
                'organization_id': organization_id,
                'report_period': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat()
                },
                'security_score': security_score,
                'events_summary': {
                    row.severity: row.count for row in events_summary
                },
                'active_alerts': active_alerts,
                'latest_backup': {
                    'date': latest_backup.completed_at.isoformat() if latest_backup else None,
                    'status': latest_backup.status if latest_backup else 'No backups found'
                },
                'recommendations': self._generate_security_recommendations(organization_id)
            }
            
        except Exception as e:
            logger.error(f"Error generating security report: {e}")
            return {}
    
    def _calculate_security_score(self, organization_id: str) -> int:
        """Calculate overall security score for organization"""
        score = 100
        
        # Deduct points for recent high-severity events
        recent_critical_events = self.db.query(SecurityEvent).filter(
            SecurityEvent.organization_id == organization_id,
            SecurityEvent.severity == 'critical',
            SecurityEvent.created_at >= datetime.utcnow() - timedelta(days=7)
        ).count()
        
        score -= (recent_critical_events * 10)
        
        # Deduct points for unresolved alerts
        unresolved_alerts = self.db.query(SecurityAlert).filter(
            SecurityAlert.organization_id == organization_id,
            SecurityAlert.status.in_(['open', 'investigating'])
        ).count()
        
        score -= (unresolved_alerts * 5)
        
        # Check backup recency
        latest_backup = self.db.query(BackupRecord).filter(
            BackupRecord.organization_id == organization_id,
            BackupRecord.status == 'completed'
        ).order_by(BackupRecord.completed_at.desc()).first()
        
        if not latest_backup or latest_backup.completed_at < datetime.utcnow() - timedelta(days=7):
            score -= 15
        
        return max(0, min(100, score))
    
    def _generate_security_recommendations(self, organization_id: str) -> List[str]:
        """Generate security recommendations"""
        recommendations = []
        
        # Check for recent backups
        latest_backup = self.db.query(BackupRecord).filter(
            BackupRecord.organization_id == organization_id,
            BackupRecord.status == 'completed'
        ).order_by(BackupRecord.completed_at.desc()).first()
        
        if not latest_backup or latest_backup.completed_at < datetime.utcnow() - timedelta(days=7):
            recommendations.append("Schedule regular automated backups")
        
        # Check for unresolved alerts
        unresolved_alerts = self.db.query(SecurityAlert).filter(
            SecurityAlert.organization_id == organization_id,
            SecurityAlert.status.in_(['open', 'investigating'])
        ).count()
        
        if unresolved_alerts > 0:
            recommendations.append(f"Review and resolve {unresolved_alerts} pending security alerts")
        
        # Check for recent security events
        recent_events = self.db.query(SecurityEvent).filter(
            SecurityEvent.organization_id == organization_id,
            SecurityEvent.severity.in_(['high', 'critical']),
            SecurityEvent.created_at >= datetime.utcnow() - timedelta(days=7)
        ).count()
        
        if recent_events > 5:
            recommendations.append("Review recent high-severity security events and implement additional controls")
        
        return recommendations
