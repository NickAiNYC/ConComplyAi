"""
Guard Agent Validator - COI Validation with OCR -> Validation -> Proof Loop
Simulates the full Guard agent workflow for investor demo
"""
import random
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, Field

# Import our new audit and telemetry modules
from packages.core.audit import (
    DecisionProof, LogicCitation, ComplianceStandard,
    create_decision_proof
)
from packages.core.telemetry import track_agent_cost


class GuardValidationResult(BaseModel):
    """Result of Guard agent COI validation"""
    document_id: str
    validation_passed: bool
    confidence: float = Field(ge=0.0, le=1.0)
    
    # Extracted fields (simulated OCR)
    has_additional_insured: bool
    has_waiver_of_subrogation: bool
    has_per_project_aggregate: bool
    general_liability_limit: float  # Per occurrence
    aggregate_limit: float
    expiration_date: datetime
    
    # Validation details
    validation_errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    
    # Cost tracking
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    
    # Audit trail
    decision_proof: Optional[DecisionProof] = None
    
    class Config:
        arbitrary_types_allowed = True
    
    def to_summary(self) -> str:
        """Generate human-readable summary"""
        status = "✅ COMPLIANT" if self.validation_passed else "❌ NON-COMPLIANT"
        lines = [
            f"Guard Agent Validation: {status}",
            f"Document: {self.document_id}",
            f"Confidence: {self.confidence:.1%}",
            "",
            "Coverage Checks:",
            f"  • Additional Insured: {'✓' if self.has_additional_insured else '✗'}",
            f"  • Waiver of Subrogation: {'✓' if self.has_waiver_of_subrogation else '✗'}",
            f"  • Per Project Aggregate: {'✓' if self.has_per_project_aggregate else '✗'}",
            f"  • General Liability: ${self.general_liability_limit:,.0f} / ${self.aggregate_limit:,.0f}",
            f"  • Expires: {self.expiration_date.strftime('%Y-%m-%d')}",
        ]
        
        if self.validation_errors:
            lines.append("")
            lines.append("Errors:")
            for error in self.validation_errors:
                lines.append(f"  ⚠ {error}")
        
        if self.warnings:
            lines.append("")
            lines.append("Warnings:")
            for warning in self.warnings:
                lines.append(f"  ⚡ {warning}")
        
        lines.append("")
        lines.append(f"Cost: ${self.cost_usd:.6f} ({self.input_tokens + self.output_tokens} tokens)")
        
        return "\n".join(lines)


@track_agent_cost(agent_name="Guard", model_name="claude-3-haiku")
def validate_coi(pdf_path: str) -> Dict[str, Any]:
    """
    Validate Certificate of Insurance (COI) through OCR -> Validation -> Proof loop
    
    This function simulates the complete Guard agent workflow:
    1. OCR Extraction: Extract fields from PDF
    2. Validation: Check against NYC construction insurance requirements
    3. Proof Generation: Create cryptographic audit trail
    
    Args:
        pdf_path: Path to COI PDF file (simulated - actual OCR not implemented)
    
    Returns:
        Dict containing GuardValidationResult and all validation details
        Must include 'input_tokens' and 'output_tokens' for cost tracking
    """
    # Generate deterministic seed from path for consistent results
    seed = sum(ord(c) for c in pdf_path) % 100
    random.seed(seed)
    
    # STEP 1: SIMULATE OCR EXTRACTION
    # In production, this would use GPT-4o Vision or Azure Document Intelligence
    # For demo, we generate realistic mock data
    
    document_id = f"COI-{datetime.now().strftime('%Y%m%d')}-{seed:03d}"
    
    # Simulate extraction - 70% are compliant
    is_compliant = seed < 70
    
    has_additional_insured = is_compliant or random.random() > 0.3
    has_waiver_of_subrogation = is_compliant or random.random() > 0.3
    has_per_project_aggregate = is_compliant or random.random() > 0.5
    
    # Generate coverage amounts
    if is_compliant:
        general_liability = random.choice([2_000_000, 3_000_000, 5_000_000])
        aggregate = general_liability * 2
    else:
        # Non-compliant: too low
        general_liability = random.choice([1_000_000, 1_500_000])
        aggregate = general_liability * 2
    
    # Expiration date
    days_until_expiry = random.randint(-30, 365)  # Some may be expired
    expiration_date = datetime.now() + timedelta(days=days_until_expiry)
    
    # Token usage for OCR + field extraction (Claude 3 Haiku)
    # PDF page image ~2000 tokens, structured output ~300 tokens
    input_tokens = 2000  # PDF + prompt
    output_tokens = 300  # Structured JSON response
    
    # STEP 2: VALIDATION LOGIC
    validation_errors = []
    warnings = []
    
    # Check Additional Insured (NYC RCNY 101-08)
    if not has_additional_insured:
        validation_errors.append(
            "CRITICAL: Additional Insured endorsement missing - violates NYC RCNY 101-08"
        )
    
    # Check Waiver of Subrogation
    if not has_waiver_of_subrogation:
        validation_errors.append(
            "CRITICAL: Waiver of Subrogation missing - contract requirement"
        )
    
    # Check Per Project Aggregate
    if not has_per_project_aggregate:
        warnings.append(
            "Per Project Aggregate not specified - may share limits with other projects"
        )
    
    # Check minimum limits (NYC construction standard: $2M/$4M)
    if general_liability < 2_000_000:
        validation_errors.append(
            f"CRITICAL: General Liability limit ${general_liability:,.0f} below minimum $2,000,000"
        )
    
    if aggregate < 4_000_000:
        validation_errors.append(
            f"CRITICAL: Aggregate limit ${aggregate:,.0f} below minimum $4,000,000"
        )
    
    # Check expiration
    if expiration_date < datetime.now():
        validation_errors.append(
            f"CRITICAL: Insurance expired on {expiration_date.strftime('%Y-%m-%d')}"
        )
    elif expiration_date < datetime.now() + timedelta(days=30):
        warnings.append(
            f"Insurance expires soon: {expiration_date.strftime('%Y-%m-%d')}"
        )
    
    # Overall validation result
    validation_passed = len(validation_errors) == 0
    confidence = 0.95 if validation_passed else 0.88
    
    # STEP 3: GENERATE DECISION PROOF
    # Build logic citations for explainability
    logic_citations = []
    
    if has_additional_insured:
        logic_citations.append(
            LogicCitation(
                standard=ComplianceStandard.NYC_RCNY_101_08,
                clause="3.3.7",
                interpretation="Certificate holder listed as Additional Insured on General Liability policy",
                confidence=0.95
            )
        )
    
    if has_waiver_of_subrogation:
        logic_citations.append(
            LogicCitation(
                standard=ComplianceStandard.WAIVER_SUBROGATION,
                clause="Contract Clause 8.2",
                interpretation="Insurer waives right to pursue certificate holder for claims",
                confidence=0.92
            )
        )
    
    if general_liability >= 2_000_000 and aggregate >= 4_000_000:
        logic_citations.append(
            LogicCitation(
                standard=ComplianceStandard.ISO_GL_MINIMUM,
                clause="AIA A201-2017 §11.1",
                interpretation=f"General Liability coverage meets minimum ${general_liability:,.0f}/${aggregate:,.0f}",
                confidence=0.98
            )
        )
    
    # Calculate financial impact (risk avoided)
    if validation_passed:
        # Compliant COI avoids project delays, legal liability
        estimated_financial_impact = 50_000  # Estimated savings from avoiding claims
    else:
        # Non-compliant COI poses risk
        estimated_financial_impact = -500_000  # Potential liability exposure
    
    # Build reasoning text
    if validation_passed:
        reasoning = (
            f"Certificate of Insurance for document {document_id} meets all NYC construction "
            f"insurance requirements. All required endorsements present, coverage limits adequate "
            f"(${general_liability:,.0f}/${aggregate:,.0f}), and policy is valid until "
            f"{expiration_date.strftime('%Y-%m-%d')}. Contractor approved for site access."
        )
    else:
        reasoning = (
            f"Certificate of Insurance for document {document_id} FAILS validation. "
            f"Critical deficiencies found: {'; '.join(validation_errors)}. "
            f"Contractor must provide updated COI before site access."
        )
    
    # Create decision proof
    decision_proof = create_decision_proof(
        agent_name="Guard",
        decision="PASS" if validation_passed else "FAIL",
        input_data={
            "document_id": document_id,
            "pdf_path": pdf_path,
            "extraction_method": "OCR_SIMULATION",
            "has_additional_insured": has_additional_insured,
            "has_waiver_of_subrogation": has_waiver_of_subrogation,
            "has_per_project_aggregate": has_per_project_aggregate,
            "general_liability_limit": general_liability,
            "aggregate_limit": aggregate,
            "expiration_date": expiration_date.isoformat(),
        },
        logic_citations=logic_citations,
        reasoning=reasoning,
        confidence=confidence,
        risk_level="LOW" if validation_passed else "HIGH",
        estimated_financial_impact=estimated_financial_impact,
        cost_usd=0.0  # Will be filled by decorator
    )
    
    # Create result object
    result = GuardValidationResult(
        document_id=document_id,
        validation_passed=validation_passed,
        confidence=confidence,
        has_additional_insured=has_additional_insured,
        has_waiver_of_subrogation=has_waiver_of_subrogation,
        has_per_project_aggregate=has_per_project_aggregate,
        general_liability_limit=general_liability,
        aggregate_limit=aggregate,
        expiration_date=expiration_date,
        validation_errors=validation_errors,
        warnings=warnings,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        decision_proof=decision_proof
    )
    
    # Return dict with token counts for decorator
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "result": result,
        "metadata": {
            "document_id": document_id,
            "success": validation_passed
        }
    }


def batch_validate_cois(pdf_paths: List[str]) -> Dict[str, Any]:
    """
    Batch validate multiple COI documents
    Returns aggregate statistics and individual results
    """
    results = []
    total_cost = 0.0
    passed = 0
    failed = 0
    
    for path in pdf_paths:
        validation = validate_coi(path)
        result = validation["result"]
        results.append(result)
        
        total_cost += validation["cost_usd"]
        if result.validation_passed:
            passed += 1
        else:
            failed += 1
    
    return {
        "total_documents": len(pdf_paths),
        "passed": passed,
        "failed": failed,
        "pass_rate": passed / len(pdf_paths) if pdf_paths else 0.0,
        "total_cost_usd": total_cost,
        "avg_cost_per_doc": total_cost / len(pdf_paths) if pdf_paths else 0.0,
        "results": results
    }
