"""
Sentinel Heartbeat Integration - High Risk Alert System
Links Sentinel monitoring with document validation

If a contractor is detected on-site but their insurance is expired,
automatically escalate to HIGH RISK alert.

Part of the Self-Healing Multi-Agent Suite
"""
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
from enum import Enum

from core.services.sentinel_service import SentinelService, MonitoringEvent, MonitoringEventType
from packages.shared.models import ExpirationStatus, AuditAction, DecisionLog


class RiskLevel(str, Enum):
    """Risk severity levels"""
    CRITICAL = "CRITICAL"  # Immediate action required
    HIGH = "HIGH"  # Urgent attention needed
    MEDIUM = "MEDIUM"  # Monitor closely
    LOW = "LOW"  # Normal operations
    INFO = "INFO"  # Informational only


class HeartbeatStatus(BaseModel):
    """Status of a contractor's on-site presence and compliance"""
    contractor_id: str
    contractor_name: str
    on_site: bool
    last_seen: Optional[datetime] = None
    
    # Compliance status
    insurance_status: ExpirationStatus
    insurance_expiration: Optional[datetime] = None
    license_status: ExpirationStatus
    license_expiration: Optional[datetime] = None
    
    # Risk assessment
    risk_level: RiskLevel
    alerts: List[str] = Field(default_factory=list)


class HighRiskAlert(BaseModel):
    """High risk alert when on-site contractor has expired documents"""
    alert_id: str
    timestamp: datetime = Field(default_factory=datetime.now)
    contractor_id: str
    contractor_name: str
    site_id: str
    
    # Risk details
    risk_level: RiskLevel
    reason: str
    violations: List[str]
    
    # Actions taken
    escalated: bool = Field(default=False)
    notification_sent: bool = Field(default=False)
    site_access_revoked: bool = Field(default=False)
    
    # Resolution
    resolved: bool = Field(default=False)
    resolution_notes: Optional[str] = None


class SentinelHeartbeat:
    """
    Integrates Sentinel monitoring with validation system
    
    Acts as a 'heartbeat' that continuously checks:
    1. Who is on-site (Sentinel detection)
    2. Their compliance status (Validator)
    3. Escalates HIGH RISK when mismatch detected
    """
    
    def __init__(
        self, 
        sentinel_service: SentinelService,
        audit_logger: Optional[Any] = None
    ):
        self.sentinel = sentinel_service
        self.audit_logger = audit_logger
        
        # Track contractor statuses
        self.contractor_statuses: Dict[str, HeartbeatStatus] = {}
        self.high_risk_alerts: List[HighRiskAlert] = []
        
        # Register callback with Sentinel
        self.sentinel.register_callback(self._on_sentinel_event)
    
    def register_contractor(
        self,
        contractor_id: str,
        contractor_name: str,
        insurance_status: ExpirationStatus,
        insurance_expiration: Optional[datetime] = None,
        license_status: ExpirationStatus = ExpirationStatus.VALID,
        license_expiration: Optional[datetime] = None
    ):
        """Register a contractor and their compliance status"""
        status = HeartbeatStatus(
            contractor_id=contractor_id,
            contractor_name=contractor_name,
            on_site=False,
            insurance_status=insurance_status,
            insurance_expiration=insurance_expiration,
            license_status=license_status,
            license_expiration=license_expiration,
            risk_level=RiskLevel.LOW
        )
        
        # Initial risk assessment
        self._assess_risk(status)
        
        self.contractor_statuses[contractor_id] = status
    
    def mark_on_site(self, contractor_id: str, site_id: str):
        """
        Mark contractor as detected on-site by Sentinel
        Triggers risk assessment
        """
        if contractor_id not in self.contractor_statuses:
            # Unknown contractor on site - automatic HIGH RISK
            self._create_high_risk_alert(
                contractor_id=contractor_id,
                contractor_name="UNKNOWN_CONTRACTOR",
                site_id=site_id,
                reason="Unknown contractor detected on-site without registration",
                violations=["Unregistered contractor", "No compliance verification"]
            )
            return
        
        status = self.contractor_statuses[contractor_id]
        status.on_site = True
        status.last_seen = datetime.now()
        
        # Re-assess risk now that they're on-site
        risk_changed = self._assess_risk(status)
        
        # If HIGH or CRITICAL risk, create alert
        if status.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
            self._create_high_risk_alert(
                contractor_id=contractor_id,
                contractor_name=status.contractor_name,
                site_id=site_id,
                reason="On-site contractor with expired/invalid compliance documents",
                violations=status.alerts
            )
    
    def mark_off_site(self, contractor_id: str):
        """Mark contractor as no longer on-site"""
        if contractor_id in self.contractor_statuses:
            self.contractor_statuses[contractor_id].on_site = False
    
    def update_compliance_status(
        self,
        contractor_id: str,
        insurance_status: Optional[ExpirationStatus] = None,
        insurance_expiration: Optional[datetime] = None,
        license_status: Optional[ExpirationStatus] = None,
        license_expiration: Optional[datetime] = None
    ):
        """Update contractor's compliance status after validation"""
        if contractor_id not in self.contractor_statuses:
            return
        
        status = self.contractor_statuses[contractor_id]
        
        if insurance_status:
            status.insurance_status = insurance_status
        if insurance_expiration:
            status.insurance_expiration = insurance_expiration
        if license_status:
            status.license_status = license_status
        if license_expiration:
            status.license_expiration = license_expiration
        
        # Re-assess risk
        old_risk = status.risk_level
        self._assess_risk(status)
        
        # If on-site and risk increased, create alert
        if status.on_site and status.risk_level > old_risk:
            if status.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
                self._create_high_risk_alert(
                    contractor_id=contractor_id,
                    contractor_name=status.contractor_name,
                    site_id="UNKNOWN",  # Site not available in this context
                    reason="Compliance status degraded for on-site contractor",
                    violations=status.alerts
                )
    
    def _assess_risk(self, status: HeartbeatStatus) -> bool:
        """
        Assess contractor risk level
        Returns True if risk level changed
        """
        old_risk = status.risk_level
        status.alerts = []
        
        # Check insurance
        if status.insurance_status == ExpirationStatus.EXPIRED:
            status.alerts.append("Insurance EXPIRED")
            if status.on_site:
                status.risk_level = RiskLevel.CRITICAL
            else:
                status.risk_level = RiskLevel.HIGH
        elif status.insurance_status == ExpirationStatus.EXPIRING_SOON:
            status.alerts.append("Insurance expiring within 30 days")
            status.risk_level = RiskLevel.MEDIUM if not status.on_site else RiskLevel.HIGH
        
        # Check license
        if status.license_status == ExpirationStatus.EXPIRED:
            status.alerts.append("License EXPIRED")
            if status.on_site:
                status.risk_level = RiskLevel.CRITICAL
            else:
                status.risk_level = RiskLevel.HIGH
        elif status.license_status == ExpirationStatus.EXPIRING_SOON:
            status.alerts.append("License expiring within 30 days")
            if status.risk_level < RiskLevel.MEDIUM:
                status.risk_level = RiskLevel.MEDIUM
        
        # If on-site with any expired items, escalate
        if status.on_site and status.alerts:
            if status.risk_level < RiskLevel.HIGH:
                status.risk_level = RiskLevel.HIGH
        
        # If no issues
        if not status.alerts:
            status.risk_level = RiskLevel.LOW
        
        return old_risk != status.risk_level
    
    def _create_high_risk_alert(
        self,
        contractor_id: str,
        contractor_name: str,
        site_id: str,
        reason: str,
        violations: List[str]
    ):
        """Create and escalate a high risk alert"""
        alert = HighRiskAlert(
            alert_id=f"RISK-{datetime.now().timestamp()}",
            contractor_id=contractor_id,
            contractor_name=contractor_name,
            site_id=site_id,
            risk_level=RiskLevel.HIGH,
            reason=reason,
            violations=violations
        )
        
        # Escalate
        alert.escalated = True
        alert.notification_sent = True
        
        # Store alert
        self.high_risk_alerts.append(alert)
        
        # Create Sentinel event
        self.sentinel.report_compliance_event(
            site_id=site_id,
            violation_data={
                'alert_id': alert.alert_id,
                'contractor_id': contractor_id,
                'contractor_name': contractor_name,
                'risk_level': 1,  # Critical priority
                'reason': reason,
                'violations': violations,
                'escalated': True
            }
        )
        
        # Log to audit trail
        if self.audit_logger:
            self._log_escalation(alert)
        
        print(f"🚨 HIGH RISK ALERT: {contractor_name} on-site at {site_id}")
        print(f"   Reason: {reason}")
        print(f"   Violations: {', '.join(violations)}")
    
    def _log_escalation(self, alert: HighRiskAlert):
        """Log escalation to audit trail"""
        decision = DecisionLog(
            decision_id=alert.alert_id,
            action=AuditAction.HIGH_RISK_ALERT,
            agent_name="sentinel_heartbeat",
            contractor_id=alert.contractor_id,
            site_id=alert.site_id,
            decision_data={
                'risk_level': alert.risk_level.value,
                'reason': alert.reason,
                'violations': alert.violations,
                'escalated': alert.escalated
            },
            reasoning="On-site contractor detected with expired compliance documents. "
                     "Automatic escalation per safety protocol.",
            confidence=1.0,  # Definitive - not AI prediction
            action_taken="Created HIGH RISK alert, notified site manager",
            cost_usd=0.0,  # No cost for escalation
            requires_human_review=True  # Always requires human review
        )
        
        if self.audit_logger:
            self.audit_logger.log_decision(decision)
    
    def _on_sentinel_event(self, event: MonitoringEvent):
        """Callback for Sentinel events"""
        # Check if this is a site update that indicates contractor presence
        if event.event_type == MonitoringEventType.SITE_UPDATE:
            contractor_id = event.data.get('contractor_id')
            site_id = event.source
            
            if contractor_id:
                self.mark_on_site(contractor_id, site_id)
    
    def get_high_risk_contractors(self) -> List[HeartbeatStatus]:
        """Get all contractors currently at HIGH or CRITICAL risk"""
        return [
            status for status in self.contractor_statuses.values()
            if status.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]
        ]
    
    def get_on_site_contractors(self) -> List[HeartbeatStatus]:
        """Get all contractors currently on-site"""
        return [
            status for status in self.contractor_statuses.values()
            if status.on_site
        ]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get heartbeat monitoring statistics"""
        total_contractors = len(self.contractor_statuses)
        on_site = len(self.get_on_site_contractors())
        high_risk = len(self.get_high_risk_contractors())
        alerts = len(self.high_risk_alerts)
        unresolved_alerts = len([a for a in self.high_risk_alerts if not a.resolved])
        
        return {
            'total_contractors': total_contractors,
            'on_site_now': on_site,
            'high_risk_contractors': high_risk,
            'total_alerts': alerts,
            'unresolved_alerts': unresolved_alerts,
            'risk_distribution': {
                'CRITICAL': len([s for s in self.contractor_statuses.values() 
                                if s.risk_level == RiskLevel.CRITICAL]),
                'HIGH': len([s for s in self.contractor_statuses.values() 
                            if s.risk_level == RiskLevel.HIGH]),
                'MEDIUM': len([s for s in self.contractor_statuses.values() 
                              if s.risk_level == RiskLevel.MEDIUM]),
                'LOW': len([s for s in self.contractor_statuses.values() 
                           if s.risk_level == RiskLevel.LOW])
            }
        }
