"""Compliance document models (OSHA, Licenses, Lien Waivers, NYC 2026 Mandates)"""
from typing import List, Optional, Literal
from datetime import datetime
from pydantic import BaseModel, Field
from .document_models import ExtractedField, ExpirationStatus


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


# =============================================================================
# 2026 NYC MANDATE MODELS - Local Law 149 & 152
# =============================================================================

class ConstructionSuperintendent(BaseModel):
    """
    Construction Superintendent tracking for Local Law 149 (One-Job Rule)
    NYC mandates that a CS can only be designated as 'Primary' on one active permit
    """
    cs_name: str = Field(description="Construction Superintendent full name")
    cs_license_number: str = Field(description="NYC CS License Number (e.g., CS-123456)")
    designation: Literal["Primary", "Backup"] = Field(
        description="Primary (onsite lead) or Backup CS"
    )
    permit_number: str = Field(description="DOB Job Filing Number")
    project_address: str = Field(description="Construction site address")
    is_active: bool = Field(
        default=True,
        description="Whether this job is currently active"
    )
    start_date: Optional[datetime] = Field(
        default=None,
        description="CS designation start date"
    )
    
    class Config:
        frozen = True


class LL149Violation(BaseModel):
    """
    Local Law 149 violation - Construction Superintendent on multiple active jobs
    
    2026 REFINEMENT: Added explainability fields per requirements
    - legal_basis: Short code + citation
    - explanation: Human-readable description
    - suggested_action: Concise remediation directive
    
    NOTE: This model is being deprecated in favor of packages.core.nyc_2026_regulations.LL149Finding
    Kept for backward compatibility.
    """
    cs_name: str
    cs_license_number: str
    active_primary_permits: List[str] = Field(
        description="List of permit numbers where CS is designated as Primary"
    )
    
    # 2026 EXPLAINABILITY FIELDS
    legal_basis: str = Field(
        default="LL149 - Local Law 149 of 2026 (The One-Job Rule)",
        description="Short code + citation string"
    )
    explanation: str = Field(
        default="Construction Superintendent designated as Primary on multiple active permits, violating one-job rule.",
        description="1-2 human sentences describing why this was flagged"
    )
    suggested_action: str = Field(
        default="Reassign superintendent or close out prior permit to satisfy one-job rule.",
        description="One concise directive for remediation"
    )
    
    violation_severity: Literal["HIGH_RISK_MANDATE", "MEDIUM", "LOW"] = Field(
        default="HIGH_RISK_MANDATE"
    )
    citation: str = Field(
        default="NYC Local Law 149 of 2026 (The One-Job Rule)",
        description="Legal citation for violation"
    )
    recommended_action: str = Field(
        default="Designate backup CS as primary on one project, or hire additional CS",
        description="Remediation guidance (deprecated, use suggested_action)"
    )
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        frozen = True


class GPS2Certification(BaseModel):
    """
    Local Law 152 (Gas Piping System) GPS2 certification tracking
    Required for buildings in specific Community Districts by 2026
    
    2026 REFINEMENT: Added explainability fields
    """
    building_bin: str = Field(description="NYC Building Identification Number")
    community_district: int = Field(
        ge=1, le=59,
        description="NYC Community District (1-59)"
    )
    has_gps2_certification: bool = Field(
        description="Whether GPS2 (gas piping inspection) is on file"
    )
    certification_date: Optional[datetime] = Field(
        default=None,
        description="Date GPS2 was filed with DOB"
    )
    in_2026_due_cycle: bool = Field(
        description="Whether building is in 2026 due cycle (CD 4,6,8,9,16)"
    )
    
    # 2026 EXPLAINABILITY FIELDS
    legal_basis: str = Field(
        default="LL152 - Local Law 152 of 2016 (Gas Piping System Periodic Inspection)",
        description="Short code + citation string"
    )
    explanation: Optional[str] = Field(
        default=None,
        description="Human-readable explanation of finding"
    )
    
    projected_fine: Optional[float] = Field(
        default=10000.0,
        description="Fine amount for non-compliance (NYC LL152: $10,000 base)"
    )
    
    class Config:
        frozen = True


class LL152Remediation(BaseModel):
    """
    Local Law 152 remediation template for Fixer agent
    Digital filing logic for missing GPS2 certifications
    
    2026 REFINEMENT: Added explainability fields per requirements
    """
    building_bin: str
    building_address: str
    community_district: int
    owner_name: str
    owner_contact: Optional[str] = None
    
    # Remediation details
    remediation_type: Literal["GPS2_FILING_REQUIRED"] = "GPS2_FILING_REQUIRED"
    deadline: datetime = Field(
        description="Compliance deadline based on CD due-cycle"
    )
    estimated_filing_cost: float = Field(
        default=2500.0,
        description="Estimated cost for GPS2 inspection and filing (typical: $2,000-$3,000)"
    )
    projected_fine_if_missed: float = Field(
        default=10000.0,
        description="DOB fine for non-compliance"
    )
    
    # 2026 EXPLAINABILITY FIELDS
    legal_basis: str = Field(
        default="LL152 - Local Law 152 of 2016 (Gas Piping System Periodic Inspection)",
        description="Short code + citation string"
    )
    explanation: str = Field(
        default="Building in 2026 LL152 due-cycle requires GPS2 gas piping inspection certification.",
        description="Human-readable explanation"
    )
    suggested_action: str = Field(
        default="Hire Licensed Master Plumber (LMP) to conduct GPS2 inspection and file certification with DOB.",
        description="Concise remediation directive"
    )
    
    # Outreach template
    subject_line: str = Field(
        default="[ACTION REQUIRED] NYC Local Law 152 GPS2 Filing Due - Avoid $10K Fine"
    )
    email_template: str = Field(
        description="Pre-drafted email for owner/agent outreach"
    )
    
    class Config:
        frozen = True
