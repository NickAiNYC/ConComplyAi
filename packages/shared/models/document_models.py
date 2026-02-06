"""Document extraction models - Shared across backend and frontend"""
from typing import List, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


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
        default=1.0,
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
    
    # Agent tracking (kept for backward compatibility, but cost details in AgentOutput)
    total_tokens: int = 0
    total_cost: float = 0.0
    processing_start: Optional[datetime] = None
    processing_end: Optional[datetime] = None
    
    class Config:
        arbitrary_types_allowed = True
