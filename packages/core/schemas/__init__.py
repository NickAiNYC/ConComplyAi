"""
Core Schemas - Unified data models for all agents
Prevents data drift between DocumentAgent (Validator) and WatchAgent (Sentinel)
"""
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


# ============================================================================
# ENUMS
# ============================================================================

class DocumentType(str, Enum):
    """Types of contractor documents"""
    COI = "COI"
    OSHA_LOG = "OSHA_LOG"
    LICENSE = "LICENSE"
    LIEN_WAIVER = "LIEN_WAIVER"
    W9 = "W9"
    PERMIT = "PERMIT"


class ExpirationStatus(str, Enum):
    """Expiration status with 48hr emergency threshold"""
    EXPIRED = "EXPIRED"
    EMERGENCY_EXPIRING = "EMERGENCY_EXPIRING"  # < 48 hours
    EXPIRING_SOON = "EXPIRING_SOON"  # < 30 days
    VALID = "VALID"
    NO_EXPIRATION = "NO_EXPIRATION"


# ============================================================================
# DECISION PROOF (XAI) - 2026 Standards
# ============================================================================

class AgentHandshake(BaseModel):
    """
    Agent-to-Agent transition tracking for governance audit
    Documents how leads pass between agents in the multi-agent system
    """
    from_agent: str = Field(description="Source agent identifier")
    to_agent: str = Field(description="Target agent identifier")
    handshake_timestamp: datetime = Field(default_factory=datetime.now)
    transition_reason: str = Field(description="Why this handoff occurred")
    data_passed: Dict[str, Any] = Field(description="Data payload transferred")
    validation_status: str = Field(description="handoff_validated|pending|failed")
    
    class Config:
        frozen = True  # Immutable after creation


class DecisionProof(BaseModel):
    """
    Explainable AI Decision Proof
    Every autonomous decision must generate this for audit trail
    """
    agent_id: str = Field(description="Unique agent identifier")
    timestamp: datetime = Field(default_factory=datetime.now)
    logic_citation: str = Field(
        description="Reference to decision rule or regulation (e.g., OSHA 1926.451)"
    )
    confidence_score: float = Field(
        ge=0.0, le=1.0,
        description="AI confidence in decision"
    )
    source_coordinates: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Bounding box or document location for traceability"
    )
    decision_type: str = Field(description="validation|outreach|escalation|watch")
    input_data: Dict[str, Any] = Field(description="Input that led to decision")
    output_action: str = Field(description="Specific action taken")
    reasoning_chain: List[str] = Field(
        default_factory=list,
        description="Step-by-step reasoning for XAI"
    )
    
    # Agent Handshake log for governance audit (Task 3)
    agent_handshake: Optional[AgentHandshake] = Field(
        default=None,
        description="Agent-to-agent transition tracking for multi-agent governance"
    )
    
    class Config:
        frozen = True  # Immutable after creation


# ============================================================================
# DOCUMENT MODELS
# ============================================================================

class SourceCoordinate(BaseModel):
    """Bounding box for extracted data"""
    page: int = Field(ge=1)
    x: float = Field(ge=0.0, le=1.0)
    y: float = Field(ge=0.0, le=1.0)
    width: float = Field(ge=0.0, le=1.0)
    height: float = Field(ge=0.0, le=1.0)


class ExtractedField(BaseModel):
    """Single extracted field with traceability"""
    field_name: str
    value: Any
    confidence: float = Field(ge=0.0, le=1.0)
    source_coordinate: Optional[SourceCoordinate] = None
    extraction_method: str = Field(default="OCR")
    validation_errors: List[str] = Field(default_factory=list)
    redacted: bool = Field(default=False)


class PIIRedaction(BaseModel):
    """PII redaction tracking"""
    field_name: str
    original_value_hash: str
    pii_type: str
    redacted_value: str
    redaction_method: str = Field(default="regex")


class BrokerContact(BaseModel):
    """
    Broker/Producer contact information extracted from COI header
    Required for BrokerLiaison agent
    """
    broker_name: ExtractedField
    broker_email: Optional[ExtractedField] = None
    broker_phone: Optional[ExtractedField] = None
    broker_address: Optional[ExtractedField] = None
    agency_name: Optional[ExtractedField] = None
    
    def has_valid_contact(self) -> bool:
        """Check if we have email OR phone for outreach"""
        has_email = (self.broker_email and 
                    self.broker_email.value and 
                    '@' in str(self.broker_email.value))
        has_phone = (self.broker_phone and 
                    self.broker_phone.value)
        return has_email or has_phone


class InsuranceCoverage(BaseModel):
    """Insurance coverage details"""
    coverage_type: str
    policy_number: str
    carrier: str
    effective_date: datetime
    expiration_date: datetime
    limit_per_occurrence: float
    aggregate_limit: float
    additional_insured: bool = Field(default=False)
    waiver_of_subrogation: bool = Field(default=False)
    per_project_aggregate: bool = Field(default=False)


class COIDocument(BaseModel):
    """Certificate of Insurance with broker contact"""
    document_id: str
    contractor_name: ExtractedField
    
    # Broker contact for BrokerLiaison agent
    broker_contact: Optional[BrokerContact] = None
    
    # Coverage details
    coverages: List[InsuranceCoverage]
    certificate_holder: ExtractedField
    description_of_operations: ExtractedField
    certificate_number: ExtractedField
    issue_date: ExtractedField
    
    # Validation results
    has_additional_insured: bool
    has_waiver_of_subrogation: bool
    has_per_project_aggregate: bool
    coverage_adequate: bool
    expiration_status: ExpirationStatus
    
    # Missing endorsements for BrokerLiaison
    missing_endorsements: List[str] = Field(default_factory=list)


class OSHALog(BaseModel):
    """OSHA 300/300A log"""
    document_id: str
    establishment_name: ExtractedField
    year: ExtractedField
    total_recordable_cases: ExtractedField
    days_away_from_work: ExtractedField
    job_transfer_restriction: ExtractedField
    other_recordable_cases: ExtractedField
    incident_rate_acceptable: bool
    validation_errors: List[str] = Field(default_factory=list)


class License(BaseModel):
    """Contractor license with emergency expiration handling"""
    document_id: str
    license_number: ExtractedField
    license_type: ExtractedField
    licensee_name: ExtractedField
    issue_date: ExtractedField
    expiration_date: ExtractedField
    issuing_authority: ExtractedField
    expiration_status: ExpirationStatus
    verified_with_authority: bool = Field(default=False)
    
    # For Presence-to-Paperwork trigger
    contractor_uid: Optional[str] = Field(
        default=None,
        description="Unique contractor ID for Sentinel matching"
    )


class LienWaiver(BaseModel):
    """Lien waiver validation"""
    document_id: str
    waiver_type: ExtractedField
    contractor_name: ExtractedField
    project_name: ExtractedField
    through_date: ExtractedField
    amount: ExtractedField
    signature_present: ExtractedField
    notarization_present: ExtractedField
    is_executed: bool
    validation_errors: List[str] = Field(default_factory=list)


class DocumentExtractionState(BaseModel):
    """
    Unified state for document extraction
    Used by both DocumentAgent (Validator) and processing pipeline
    """
    document_id: str
    document_type: DocumentType
    file_path: Optional[str] = None
    file_url: Optional[str] = None
    
    # Quality
    document_quality_score: float = Field(default=1.0, ge=0.0, le=1.0)
    is_skewed: bool = Field(default=False)
    is_crumpled: bool = Field(default=False)
    is_multi_page: bool = Field(default=False)
    page_count: int = Field(default=1, ge=1)
    
    # Extraction
    extracted_fields: List[ExtractedField] = Field(default_factory=list)
    pii_redactions: List[PIIRedaction] = Field(default_factory=list)
    
    # Validation
    validation_passed: bool = Field(default=False)
    validation_errors: List[str] = Field(default_factory=list)
    
    # Decision proofs for XAI
    decision_proofs: List[DecisionProof] = Field(default_factory=list)
    
    # Cost tracking
    total_tokens: int = 0
    total_cost: float = 0.0
    processing_start: Optional[datetime] = None
    processing_end: Optional[datetime] = None
    
    class Config:
        arbitrary_types_allowed = True


# ============================================================================
# SCOPESIGNAL & FEASIBILITY - 2027 Standards
# ============================================================================

class LeadStatus(str, Enum):
    """Status of a ScopeSignal lead/opportunity"""
    CONTESTABLE = "CONTESTABLE"  # High-confidence opportunity
    MONITORING = "MONITORING"  # Under surveillance
    QUALIFIED = "QUALIFIED"  # Passed feasibility
    DISQUALIFIED = "DISQUALIFIED"  # Failed feasibility
    CLOSED_WON = "CLOSED_WON"
    CLOSED_LOST = "CLOSED_LOST"


class AgencyRequirement(str, Enum):
    """Insurance agency compliance requirements"""
    SCA = "SCA"  # School Construction Authority
    DDC = "DDC"  # Department of Design and Construction
    HPD = "HPD"  # Housing Preservation and Development
    DOT = "DOT"  # Department of Transportation


class ScopeSignal(BaseModel):
    """
    Lead/Opportunity from ConComply-Scope Suite
    Links vision detections to business opportunities
    """
    signal_id: str = Field(description="Unique signal identifier")
    project_id: str = Field(description="Project being monitored")
    project_name: str
    project_address: str
    
    # Status tracking
    status: LeadStatus = Field(default=LeadStatus.CONTESTABLE)
    detected_at: datetime = Field(default_factory=datetime.now)
    
    # Compliance gaps detected
    missing_endorsements: List[str] = Field(default_factory=list)
    insurance_gaps: List[str] = Field(default_factory=list)
    agency_requirements: List[AgencyRequirement] = Field(default_factory=list)
    
    # Vision correlation (Task 2)
    sentinel_detection_id: Optional[str] = Field(
        default=None,
        description="Link to Sentinel-Scope vision detection"
    )
    has_active_monitoring: bool = Field(
        default=False,
        description="True if Sentinel is already watching this project"
    )
    
    # Estimator support
    site_status_memo: Optional[str] = Field(
        default=None,
        description="Auto-generated memo for estimator when CONTESTABLE + monitoring"
    )
    
    # Broker contact for outreach
    broker_contact: Optional[BrokerContact] = None
    contractor_name: str
    
    # Feasibility link
    feasibility_score: Optional[float] = Field(
        default=None,
        ge=0.0, le=100.0,
        description="Likelihood of winning bid with current compliance"
    )


class FeasibilityScore(BaseModel):
    """
    Feasibility assessment with profitability drain prediction
    Uses 'Skeptical' veteran logic for risk calculations
    """
    signal_id: str = Field(description="Associated ScopeSignal")
    project_id: str
    
    # Core feasibility
    overall_score: float = Field(ge=0.0, le=100.0)
    confidence: float = Field(ge=0.0, le=1.0)
    
    # Insurance gap analysis
    current_insurance_gaps: List[str] = Field(default_factory=list)
    required_endorsements: List[str] = Field(default_factory=list)
    
    # Predictive Risk (Task 4) - Profitability Drain
    projected_premium_increase: float = Field(
        description="Estimated cost of additional insurance (USD)"
    )
    projected_profitability_drain: float = Field(
        description="% profit margin lost to insurance gaps"
    )
    estimated_bid_adjustment: float = Field(
        description="Additional bid amount needed to cover gaps (USD)"
    )
    
    # Skeptical veteran logic factors
    risk_factors: Dict[str, float] = Field(
        default_factory=dict,
        description="Breakdown of risk multipliers (e.g., 'agency_strictness': 1.3)"
    )
    
    # Cost efficiency tracking
    calculation_tokens: int = Field(default=0)
    calculation_cost: float = Field(default=0.0)
    
    # Decision support
    recommendation: str = Field(
        description="bid_with_caution|bid_after_compliance|do_not_bid"
    )
    reasoning: List[str] = Field(
        default_factory=list,
        description="Step-by-step reasoning for recommendation"
    )
    
    assessed_at: datetime = Field(default_factory=datetime.now)
    assessed_by_agent: str = Field(default="FeasibilityAgent")


class EndorsementRequest(BaseModel):
    """
    Insurance endorsement request drafted by BrokerLiaison agent
    Sent to broker to fix compliance gaps
    """
    request_id: str
    signal_id: str  # Link to ScopeSignal
    project_name: str
    contractor_name: str
    
    # Target recipient
    broker_contact: BrokerContact
    
    # Request details
    agency_requirement: AgencyRequirement
    required_endorsements: List[str]
    urgency_level: str = Field(description="critical|high|standard")
    
    # Draft content
    subject_line: str
    email_body: str
    
    # Status
    drafted_at: datetime = Field(default_factory=datetime.now)
    sent_at: Optional[datetime] = None
    broker_responded_at: Optional[datetime] = None
    status: str = Field(default="drafted", description="drafted|sent|responded|fulfilled")
    
    # Governance
    decision_proof: Optional[DecisionProof] = None
