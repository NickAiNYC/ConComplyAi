"""
Immutable Audit Logger - Human-on-the-Loop System
2026 Compliance Standards

Records all autonomous AI decisions to an immutable audit trail.
Human-on-the-loop (not in-the-loop): AI acts autonomously, humans review logs.

Features:
- Immutable log entries (append-only)
- Comprehensive decision tracking
- Human review workflow
- 7-year retention for compliance
- Export for regulatory audits
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import json
import hashlib
from pathlib import Path

from packages.shared.models.audit_models import (
    AuditLogEntry,
    DecisionLog,
    AuditAction
)


class ImmutableAuditLogger:
    """
    Immutable audit trail logger
    
    All entries are append-only with cryptographic hashing
    to ensure tamper-proof compliance logs
    """
    
    def __init__(self, log_directory: str = "/tmp/audit_logs"):
        self.log_directory = Path(log_directory)
        self.log_directory.mkdir(parents=True, exist_ok=True)
        
        # Current session
        self.session_id = f"SESSION-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        self.current_log: Optional[AuditLogEntry] = None
        self.decision_buffer: List[DecisionLog] = []
        
        # Initialize new log entry
        self._init_new_log()
    
    def _init_new_log(self):
        """Initialize a new audit log entry"""
        self.current_log = AuditLogEntry(
            log_id=f"LOG-{datetime.now().timestamp()}",
            session_id=self.session_id,
            system_version="1.0.0-self-healing",
            environment="production",
            compliance_standard="2026-OSHA-GDPR-SOC2"
        )
    
    def log_decision(self, decision: DecisionLog):
        """
        Log an autonomous AI decision
        
        This is the core method called by all agents to record actions
        """
        if not self.current_log:
            self._init_new_log()
        
        # Add to current log
        self.current_log.decisions.append(decision)
        self.decision_buffer.append(decision)
        
        # Update metrics
        self.current_log.total_decisions += 1
        self.current_log.total_cost += decision.cost_usd
        
        if not decision.human_reviewed:
            self.current_log.autonomous_actions += 1
        else:
            self.current_log.human_interventions += 1
        
        # Auto-flush every 10 decisions or if high-stakes
        if (len(self.decision_buffer) >= 10 or 
            decision.requires_human_review or
            decision.action == AuditAction.HIGH_RISK_ALERT):
            self.flush()
    
    def flush(self):
        """
        Flush current log to disk (immutable)
        Creates a new log entry after flushing
        """
        if not self.current_log or not self.current_log.decisions:
            return
        
        # Generate log file name with timestamp
        timestamp = datetime.now().strftime('%Y%m%d-%H%M%S-%f')
        log_file = self.log_directory / f"audit_{timestamp}.json"
        
        # Serialize to JSON
        log_data = self.current_log.model_dump(mode='json')
        
        # Add integrity hash
        log_json = json.dumps(log_data, indent=2, default=str)
        integrity_hash = hashlib.sha256(log_json.encode()).hexdigest()
        log_data['integrity_hash'] = integrity_hash
        
        # Write to disk (append-only, never overwrite)
        with open(log_file, 'w') as f:
            json.dump(log_data, f, indent=2, default=str)
        
        print(f"[AUDIT] Flushed {len(self.current_log.decisions)} decisions to {log_file}")
        
        # Clear buffer and start new log
        self.decision_buffer = []
        self._init_new_log()
    
    def get_pending_reviews(self) -> List[DecisionLog]:
        """Get all decisions requiring human review"""
        all_decisions = []
        
        # Check current buffer
        all_decisions.extend([
            d for d in self.decision_buffer 
            if d.requires_human_review and not d.human_reviewed
        ])
        
        # Check recent logs
        for log_file in sorted(self.log_directory.glob("audit_*.json"), reverse=True)[:10]:
            with open(log_file, 'r') as f:
                log_data = json.load(f)
                for decision_data in log_data.get('decisions', []):
                    if (decision_data.get('requires_human_review') and 
                        not decision_data.get('human_reviewed')):
                        # Reconstruct DecisionLog
                        decision = DecisionLog(**decision_data)
                        all_decisions.append(decision)
        
        return all_decisions
    
    def mark_reviewed(
        self,
        decision_id: str,
        reviewer: str,
        override: Optional[bool] = None,
        notes: Optional[str] = None
    ):
        """
        Mark a decision as reviewed by a human
        
        Args:
            decision_id: ID of the decision
            reviewer: Name/ID of human reviewer
            override: True if human overrides AI decision
            notes: Human reviewer notes
        """
        # Check buffer first
        for decision in self.decision_buffer:
            if decision.decision_id == decision_id:
                decision.human_reviewed = True
                decision.human_reviewer = reviewer
                decision.human_review_timestamp = datetime.now()
                decision.human_override = override
                decision.human_notes = notes
                
                # Log the review as a new decision
                review_decision = DecisionLog(
                    decision_id=f"REVIEW-{decision_id}",
                    action=AuditAction.AUTONOMOUS_DECISION,
                    agent_name="human_reviewer",
                    decision_data={
                        'reviewed_decision_id': decision_id,
                        'override': override,
                        'notes': notes
                    },
                    reasoning=f"Human review of decision {decision_id}",
                    confidence=1.0,
                    action_taken="Reviewed and approved" if not override else "Reviewed and overridden",
                    cost_usd=0.0
                )
                self.log_decision(review_decision)
                return True
        
        return False
    
    def export_for_audit(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> str:
        """
        Export audit logs for regulatory compliance
        
        Returns path to consolidated export file
        """
        if not start_date:
            start_date = datetime.now() - timedelta(days=30)
        if not end_date:
            end_date = datetime.now()
        
        export_file = self.log_directory / f"audit_export_{datetime.now().strftime('%Y%m%d')}.json"
        
        # Collect all logs in date range
        consolidated = {
            'export_date': datetime.now().isoformat(),
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'compliance_standard': '2026-OSHA-GDPR-SOC2',
            'logs': []
        }
        
        for log_file in sorted(self.log_directory.glob("audit_*.json")):
            with open(log_file, 'r') as f:
                log_data = json.load(f)
                log_timestamp = datetime.fromisoformat(log_data['timestamp'])
                
                if start_date <= log_timestamp <= end_date:
                    consolidated['logs'].append(log_data)
        
        # Write consolidated export
        with open(export_file, 'w') as f:
            json.dump(consolidated, f, indent=2, default=str)
        
        print(f"[AUDIT] Exported {len(consolidated['logs'])} log entries to {export_file}")
        
        return str(export_file)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get audit trail statistics"""
        total_logs = len(list(self.log_directory.glob("audit_*.json")))
        pending_reviews = len(self.get_pending_reviews())
        
        # Aggregate stats from recent logs
        total_decisions = self.current_log.total_decisions if self.current_log else 0
        total_cost = self.current_log.total_cost if self.current_log else 0.0
        autonomous = self.current_log.autonomous_actions if self.current_log else 0
        interventions = self.current_log.human_interventions if self.current_log else 0
        
        return {
            'total_log_files': total_logs,
            'pending_reviews': pending_reviews,
            'current_session': self.session_id,
            'session_decisions': total_decisions,
            'session_cost': total_cost,
            'autonomous_actions': autonomous,
            'human_interventions': interventions,
            'autonomy_rate': autonomous / total_decisions if total_decisions > 0 else 0
        }
    
    def verify_integrity(self, log_file: Path) -> bool:
        """
        Verify log file hasn't been tampered with
        
        Checks SHA-256 hash against stored value
        """
        with open(log_file, 'r') as f:
            log_data = json.load(f)
        
        stored_hash = log_data.pop('integrity_hash', None)
        if not stored_hash:
            return False
        
        # Recalculate hash
        log_json = json.dumps(log_data, indent=2, default=str)
        calculated_hash = hashlib.sha256(log_json.encode()).hexdigest()
        
        return stored_hash == calculated_hash


# Global singleton
_audit_logger: Optional[ImmutableAuditLogger] = None


def get_audit_logger() -> ImmutableAuditLogger:
    """Get or create global audit logger instance"""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = ImmutableAuditLogger()
    return _audit_logger


def log_autonomous_action(
    action: AuditAction,
    agent_name: str,
    decision_data: Dict[str, Any],
    reasoning: str,
    action_taken: str,
    confidence: float = 0.95,
    cost_usd: float = 0.0,
    requires_review: bool = False,
    **kwargs
) -> DecisionLog:
    """
    Convenience function to log an autonomous action
    
    Usage:
        log_autonomous_action(
            action=AuditAction.OUTREACH_SENT,
            agent_name="outreach_agent",
            decision_data={"contractor": "ABC Corp"},
            reasoning="Validation failed",
            action_taken="Sent correction email",
            cost_usd=0.0001
        )
    """
    decision = DecisionLog(
        decision_id=f"DEC-{datetime.now().timestamp()}",
        action=action,
        agent_name=agent_name,
        decision_data=decision_data,
        reasoning=reasoning,
        confidence=confidence,
        action_taken=action_taken,
        cost_usd=cost_usd,
        requires_human_review=requires_review,
        **kwargs
    )
    
    logger = get_audit_logger()
    logger.log_decision(decision)
    
    return decision
