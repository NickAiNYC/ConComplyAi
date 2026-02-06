"""Pydantic models for Construction Compliance AI - Type-safe contracts"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class RiskLevel(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class Violation(BaseModel):
    """Single violation detected by vision AI"""
    violation_id: str
    category: str
    description: str
    confidence: float = Field(ge=0.0, le=1.0)
    risk_level: RiskLevel
    estimated_fine: float
    location: str


class PermitData(BaseModel):
    """NYC DOB/HPD permit information"""
    site_id: str
    permit_number: Optional[str]
    status: str
    expiration_date: Optional[datetime]
    violations_on_record: int


class AgentOutput(BaseModel):
    """Standardized agent output for state tracking"""
    agent_name: str
    status: str
    tokens_used: int
    usd_cost: float
    timestamp: datetime
    data: Dict[str, Any]


class ConstructionState(BaseModel):
    """LangGraph state - complete system state"""
    site_id: str
    image_url: Optional[str] = None
    violations: List[Violation] = Field(default_factory=list)
    permit_data: Optional[PermitData] = None
    risk_score: float = 0.0
    estimated_savings: float = 0.0
    agent_outputs: List[AgentOutput] = Field(default_factory=list)
    agent_errors: List[str] = Field(default_factory=list)
    total_tokens: int = 0
    total_cost: float = 0.0
    processing_start: Optional[datetime] = None
    processing_end: Optional[datetime] = None
    
    class Config:
        arbitrary_types_allowed = True


# ============================================================================
# CONTRACTOR DOCUMENT VALIDATION MODELS
# ============================================================================

class DocumentType(str, Enum):
    """Types of contractor documents"""
    COI = "COI"  # Certificate of Insurance
    OSHA_LOG = "OSHA_LOG"
    LICENSE = "LICENSE"
    LIEN_WAIVER = "LIEN_WAIVER"
    W9 = "W9"
    PERMIT = "PERMIT"


class ExpirationStatus(str, Enum):
    """Expiration status classification"""
    EXPIRED = "EXPIRED"
    EXPIRING_SOON = "EXPIRING_SOON"  # Within 30 days
    VALID = "VALID"
    NO_EXPIRATION = "NO_EXPIRATION"


class SourceCoordinate(BaseModel):
    """Bounding box coordinates for extracted data - maps to original document"""
    page: int = Field(ge=1, description="Page number (1-indexed)")
    x: float = Field(ge=0.0, le=1.0, description="Left position (normalized 0-1)")
    y: float = Field(ge=0.0, le=1.0, description="Top position (normalized 0-1)")
    width: float = Field(ge=0.0, le=1.0, description="Width (normalized 0-1)")
    height: float = Field(ge=0.0, le=1.0, description="Height (normalized 0-1)")


class ExtractedField(BaseModel):
    """Single extracted field with audit trail"""
    field_name: str
    value: Any
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score 0-1")
    source_coordinate: Optional[SourceCoordinate] = None
    extraction_method: str = Field(default="OCR", description="OCR, LLM, Manual")
    validation_errors: List[str] = Field(default_factory=list)
    redacted: bool = Field(default=False, description="PII redaction applied")


class InsuranceCoverage(BaseModel):
    """Insurance coverage details for COI validation"""
    coverage_type: str  # General Liability, Workers Comp, Auto, etc.
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
    """Certificate of Insurance - Domain-specific validation"""
    document_id: str
    contractor_name: ExtractedField
    producer_name: ExtractedField
    insured_address: ExtractedField
    coverages: List[InsuranceCoverage]
    certificate_holder: ExtractedField
    description_of_operations: ExtractedField
    certificate_number: ExtractedField
    issue_date: ExtractedField
    
    # Validation results
    has_additional_insured: bool
    has_waiver_of_subrogation: bool
    has_per_project_aggregate: bool
    coverage_adequate: bool = Field(
        description="All required coverages meet minimum limits"
    )
    expiration_status: ExpirationStatus


class OSHALog(BaseModel):
    """OSHA 300/300A log validation"""
    document_id: str
    establishment_name: ExtractedField
    year: ExtractedField
    total_recordable_cases: ExtractedField
    days_away_from_work: ExtractedField
    job_transfer_restriction: ExtractedField
    other_recordable_cases: ExtractedField
    
    # Validation
    incident_rate_acceptable: bool = Field(
        description="Incident rate below industry average"
    )
    validation_errors: List[str] = Field(default_factory=list)


class License(BaseModel):
    """Contractor license validation"""
    document_id: str
    license_number: ExtractedField
    license_type: ExtractedField
    licensee_name: ExtractedField
    issue_date: ExtractedField
    expiration_date: ExtractedField
    issuing_authority: ExtractedField
    
    # Validation
    expiration_status: ExpirationStatus
    verified_with_authority: bool = Field(
        default=False,
        description="License number verified with issuing authority"
    )


class LienWaiver(BaseModel):
    """Lien waiver validation"""
    document_id: str
    waiver_type: ExtractedField  # Conditional/Unconditional, Partial/Final
    contractor_name: ExtractedField
    project_name: ExtractedField
    through_date: ExtractedField
    amount: ExtractedField
    signature_present: ExtractedField
    notarization_present: ExtractedField
    
    # Validation
    is_executed: bool = Field(description="Properly signed and notarized")
    validation_errors: List[str] = Field(default_factory=list)


class PIIRedaction(BaseModel):
    """PII redaction tracking"""
    field_name: str
    original_value_hash: str = Field(description="SHA-256 hash of original")
    pii_type: str  # SSN, Phone, Email, Address, etc.
    redacted_value: str = Field(description="Masked value (e.g., ***-**-1234)")
    redaction_method: str = Field(default="regex", description="Detection method")


class DocumentExtractionState(BaseModel):
    """State for document extraction workflow"""
    document_id: str
    document_type: DocumentType
    file_path: Optional[str] = None
    file_url: Optional[str] = None
    
    # Quality checks
    document_quality_score: float = Field(
        ge=0.0, le=1.0,
        description="Quality score: skew, blur, contrast"
    )
    is_skewed: bool = Field(default=False)
    is_crumpled: bool = Field(default=False)
    is_multi_page: bool = Field(default=False)
    page_count: int = Field(default=1, ge=1)
    
    # Extraction results
    extracted_fields: List[ExtractedField] = Field(default_factory=list)
    pii_redactions: List[PIIRedaction] = Field(default_factory=list)
    
    # Validation
    validation_passed: bool = Field(default=False)
    validation_errors: List[str] = Field(default_factory=list)
    
    # Agent tracking
    agent_outputs: List[AgentOutput] = Field(default_factory=list)
    total_tokens: int = 0
    total_cost: float = 0.0
    processing_start: Optional[datetime] = None
    processing_end: Optional[datetime] = None
    
    class Config:
        arbitrary_types_allowed = True
