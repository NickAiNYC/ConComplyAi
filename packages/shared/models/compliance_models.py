"""Compliance document models (OSHA, Licenses, Lien Waivers)"""
from typing import List
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
