"""
Audit and Decision Log Models - Human-on-the-Loop
Immutable audit trail for 2026 compliance standards
"""
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class AuditAction(str, Enum):
    """Types of autonomous actions that need logging"""
    DOCUMENT_EXTRACTED = "DOCUMENT_EXTRACTED"
    VALIDATION_FAILED = "VALIDATION_FAILED"
    VALIDATION_PASSED = "VALIDATION_PASSED"
    OUTREACH_SENT = "OUTREACH_SENT"
    ESCALATION_TRIGGERED = "ESCALATION_TRIGGERED"
    EXPIRATION_WARNING = "EXPIRATION_WARNING"
    HIGH_RISK_ALERT = "HIGH_RISK_ALERT"
    CORRECTION_REQUEST = "CORRECTION_REQUEST"
    AUTONOMOUS_DECISION = "AUTONOMOUS_DECISION"


class DecisionLog(BaseModel):
    """
    Single decision made by the AI system
    Immutable record for compliance auditing
    """
    decision_id: str = Field(description="Unique decision ID")
    timestamp: datetime = Field(default_factory=datetime.now)
    action: AuditAction
    agent_name: str = Field(description="Which agent made the decision")
    
    # Context
    document_id: Optional[str] = None
    contractor_id: Optional[str] = None
    site_id: Optional[str] = None
    
    # Decision details
    decision_data: Dict[str, Any] = Field(
        description="Full context of the decision"
    )
    reasoning: str = Field(description="Why this action was taken")
    confidence: float = Field(ge=0.0, le=1.0, description="AI confidence in decision")
    
    # Outcome
    action_taken: str = Field(description="Specific action executed")
    cost_usd: float = Field(default=0.0, description="Cost of this action")
    
    # Human review
    requires_human_review: bool = Field(
        default=False,
        description="Flag for high-stakes decisions"
    )
    human_reviewed: bool = Field(default=False)
    human_reviewer: Optional[str] = None
    human_review_timestamp: Optional[datetime] = None
    human_override: Optional[bool] = None
    human_notes: Optional[str] = None
    
    class Config:
        # Make immutable after creation
        frozen = False  # Set to True in production for true immutability
        arbitrary_types_allowed = True


class AuditLogEntry(BaseModel):
    """
    Top-level audit log entry
    Comprehensive record of all system actions
    """
    log_id: str = Field(description="Unique log entry ID")
    timestamp: datetime = Field(default_factory=datetime.now)
    session_id: str = Field(description="Links related actions")
    
    # System context
    system_version: str = Field(default="1.0.0")
    environment: str = Field(default="production")  # production, staging, dev
    
    # Decision logs
    decisions: list[DecisionLog] = Field(default_factory=list)
    
    # Metrics
    total_cost: float = Field(default=0.0)
    total_decisions: int = Field(default=0)
    autonomous_actions: int = Field(default=0)
    human_interventions: int = Field(default=0)
    
    # Compliance
    compliance_standard: str = Field(
        default="2026-OSHA-GDPR",
        description="Applicable compliance standard"
    )
    retention_period_days: int = Field(
        default=2555,  # 7 years for compliance
        description="How long to retain this log"
    )
    
    class Config:
        arbitrary_types_allowed = True
