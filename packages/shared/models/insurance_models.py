"""Insurance-specific models"""
from typing import List
from pydantic import BaseModel, Field
from datetime import datetime
from .document_models import ExtractedField, ExpirationStatus


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
