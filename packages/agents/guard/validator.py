"""
Guard Agent Validator - COI Validation with OCR -> Validation -> Proof Loop
Simulates the full Guard agent workflow for investor demo

2026 UPGRADE: Added Local Law 149 (One-Job Rule) validation for Construction Superintendents
2026 REFINEMENT: Centralized LL149 checks using packages.core.nyc_2026_regulations

BINDING CONSTRAINTS:
- IF OCR confidence < 95%, RETURN status="ILLEGIBLE"
- IF deficiency found, citations MUST reference specific regulation
- IF CS has >1 active Primary designation, trigger HIGH_RISK_MANDATE alert (LL149)
- Integration: MUST use @track_agent_cost decorator
- Integration: MUST use DecisionProof.generate()
- Cost target: Keep total under $0.010 (10% margin above $0.007 target)
"""
import random
import json
from typing import Dict, Any, List, Optional, Literal
from datetime import datetime, timedelta
from pathlib import Path
from pydantic import BaseModel, Field

# Import our new audit and telemetry modules
from packages.core.audit import (
    DecisionProof, LogicCitation, ComplianceStandard,
    create_decision_proof
)
from packages.core.telemetry import track_agent_cost
from packages.core.nyc_2026_regulations import (
    is_ll149_superintendent_conflict,
    LL149Finding,
    format_legal_basis
)


class ComplianceResult(BaseModel):
    """Guard Agent output - frozen for audit trail"""
    status: Literal["APPROVED", "REJECTED", "ILLEGIBLE", "PENDING_FIX"]
    deficiency_list: List[str] = Field(default_factory=list)
    decision_proof: str = Field(description="SHA-256 hash from DecisionProof")
    confidence_score: float = Field(ge=0.0, le=1.0)
    processing_cost: float = Field(description="USD cost from telemetry")
    document_id: str
    ocr_confidence: float = Field(ge=0.0, le=1.0, description="OCR legibility score")
    page_count: int = Field(ge=1, description="Number of pages processed")
    citations: List[str] = Field(default_factory=list, description="Regulatory citations for deficiencies")
    
    class Config:
        frozen = True


def _simulate_ocr(pdf_path: str) -> Dict[str, Any]:
    """
    Simulate Tesseract OCR extraction
    In production: Use pytesseract or Azure Document Intelligence
    
    Returns:
        Dict with extracted text, confidence, and page count
    """
    # Generate deterministic seed from path
    seed = sum(ord(c) for c in pdf_path) % 100
    random.seed(seed)
    
    # Determine document quality based on filename
    filename = Path(pdf_path).name.lower()
    
    if "illegible" in filename:
        ocr_confidence = random.uniform(0.65, 0.90)  # Below 95% threshold
        page_count = 1
        extracted_text = "POOR QUALITY - UNABLE TO EXTRACT RELIABLY"
    elif "poor" in filename or "scan" in filename:
        ocr_confidence = random.uniform(0.90, 0.94)  # Just below threshold
        page_count = random.randint(1, 2)
        extracted_text = "Partially legible certificate of insurance..."
    else:
        ocr_confidence = random.uniform(0.95, 0.99)  # Good quality
        page_count = random.randint(1, 3)
        extracted_text = """
        CERTIFICATE OF INSURANCE
        Producer: ABC Insurance Agency
        Insured: XYZ Construction Corp
        
        COVERAGES:
        General Liability: $2,000,000 per occurrence / $4,000,000 aggregate
        Workers Compensation: Statutory Limits
        Additional Insured: Certificate Holder is Additional Insured
        Waiver of Subrogation: Applicable
        Per Project Aggregate: Yes
        
        Effective Date: 01/01/2026
        Expiration Date: 12/31/2026
        """
    
    return {
        "ocr_confidence": ocr_confidence,
        "page_count": page_count,
        "extracted_text": extracted_text,
        "processing_time_ms": page_count * 200  # 200ms per page
    }


def _load_validation_rules() -> Dict[str, Any]:
    """
    Load NYC SCA validation rules
    In production: Load from rulesets/nyc_sca_requirements.json
    """
    return {
        "minimum_gl_per_occurrence": 2_000_000,
        "minimum_gl_aggregate": 4_000_000,
        "required_endorsements": [
            "additional_insured",
            "waiver_of_subrogation"
        ],
        "recommended_endorsements": [
            "per_project_aggregate"
        ],
        "minimum_ocr_confidence": 0.95,
        "citations": {
            "additional_insured": "NYC RCNY §101-08(c)(3)",
            "waiver_of_subrogation": "NYC SCA Bulletin 2024-03",
            "minimum_limits": "AIA A201-2017 §11.1",
            "expired_policy": "NYC Building Code §3301.9"
        }
    }


def _parse_coi_fields(extracted_text: str, pdf_path: str) -> Dict[str, Any]:
    """
    Simulate Claude Haiku API for intelligent field extraction
    In production: Call Claude Haiku with structured output
    """
    seed = sum(ord(c) for c in pdf_path) % 100
    random.seed(seed)
    
    filename = Path(pdf_path).name.lower()
    
    # Determine document characteristics
    if "compliant" in filename:
        # Fully compliant document
        has_additional_insured = True
        has_waiver = True
        has_per_project = True
        gl_per_occurrence = 2_000_000
        gl_aggregate = 4_000_000
        days_until_expiry = 300
    elif "missing_waiver" in filename or "missing" in filename:
        # Missing waiver of subrogation
        has_additional_insured = True
        has_waiver = False
        has_per_project = True
        gl_per_occurrence = 2_000_000
        gl_aggregate = 4_000_000
        days_until_expiry = 300
    elif "low_limits" in filename:
        # Limits too low
        has_additional_insured = True
        has_waiver = True
        has_per_project = False
        gl_per_occurrence = 1_000_000  # Too low
        gl_aggregate = 2_000_000  # Too low
        days_until_expiry = 300
    elif "expired" in filename:
        # Expired policy
        has_additional_insured = True
        has_waiver = True
        has_per_project = True
        gl_per_occurrence = 2_000_000
        gl_aggregate = 4_000_000
        days_until_expiry = -30  # Expired 30 days ago
    else:
        # Random variation for other files
        has_additional_insured = seed < 80
        has_waiver = seed < 70
        has_per_project = seed < 60
        gl_per_occurrence = random.choice([1_000_000, 2_000_000, 3_000_000])
        gl_aggregate = gl_per_occurrence * 2
        days_until_expiry = random.randint(-30, 365)
    
    expiration_date = datetime.now() + timedelta(days=days_until_expiry)
    
    return {
        "has_additional_insured": has_additional_insured,
        "has_waiver_of_subrogation": has_waiver,
        "has_per_project_aggregate": has_per_project,
        "gl_per_occurrence": gl_per_occurrence,
        "gl_aggregate": gl_aggregate,
        "expiration_date": expiration_date,
        "policy_holder": "XYZ Construction Corp",
        "producer": "ABC Insurance Agency"
    }


def _check_cs_ll149_compliance(
    permit_number: Optional[str] = None,
    cs_name: Optional[str] = None,
    cs_license: Optional[str] = None
) -> Optional[LL149Finding]:
    """
    Check Construction Superintendent compliance with Local Law 149 (One-Job Rule)
    
    2026 REFINEMENT: Now uses centralized is_ll149_superintendent_conflict() helper
    from packages.core.nyc_2026_regulations module.
    
    NYC Local Law 149 of 2026: A Construction Superintendent can only be designated
    as 'Primary' on ONE active permit at a time.
    
    Args:
        permit_number: DOB Job Filing Number from Scout
        cs_name: Construction Superintendent name (if provided in permit data)
        cs_license: CS License number if available
    
    Returns:
        LL149Finding object if violation detected, None if compliant
    """
    # In production: Query NYC DOB BIS database for CS designations
    # For demo: Simulate database lookup with deterministic violations
    
    if not permit_number or not cs_name:
        # Cannot check without permit/CS data
        return None
    
    # Generate license number if not provided
    if not cs_license:
        cs_license = f"CS-{hash(cs_name) % 999999:06d}"
    
    # Simulate CS database - some CS names trigger violations for demo
    # In production: SELECT * FROM cs_designations WHERE cs_license = ? AND is_active = TRUE
    violation_trigger_names = [
        "John Smith",
        "Michael Chen", 
        "David Rodriguez",
        "Sarah Johnson"
    ]
    
    if cs_name in violation_trigger_names:
        # Simulate finding CS on multiple active jobs
        active_permits = [
            {"permit_number": permit_number, "designation": "Primary", "is_active": True},
            {"permit_number": f"{int(permit_number) + 1:09d}", "designation": "Primary", "is_active": True},
        ]
        
        # Use centralized helper from nyc_2026_regulations
        return is_ll149_superintendent_conflict(
            cs_license_number=cs_license,
            active_permits=active_permits,
            cs_name=cs_name
        )
    
    return None


def _get_permit_cs_info(permit_number: Optional[str]) -> Optional[Dict[str, Any]]:
    """
    Simulate looking up Construction Superintendent info from permit data
    In production: Query NYC DOB BIS API or internal database
    
    Returns:
        Dict with CS info if available, None otherwise
    """
    if not permit_number:
        return None
    
    # Simulate CS data based on permit number
    # For permits ending in certain digits, return CS info for testing
    if permit_number and (int(permit_number[-2:]) % 3 == 0):
        cs_names = [
            "John Smith",
            "Michael Chen",
            "David Rodriguez", 
            "Sarah Johnson",
            "Robert Williams"
        ]
        # Pick CS based on permit number
        cs_idx = int(permit_number[-3:]) % len(cs_names)
        cs_name = cs_names[cs_idx]
        
        return {
            "cs_name": cs_name,
            "cs_license": f"CS-{hash(cs_name) % 999999:06d}",
            "designation": "Primary"
        }
    
    return None


@track_agent_cost(agent_name="Guard", model_name="claude-3-haiku")
def validate_coi(
    pdf_path: Path,
    permit_number: Optional[str] = None,
    check_ll149: bool = True
) -> Dict[str, Any]:
    """
    Validate Certificate of Insurance through OCR -> Validation -> Proof loop
    
    2026 UPGRADE: Now includes Local Law 149 (One-Job Rule) validation
    
    Args:
        pdf_path: Path to COI PDF file (simulated - actual OCR not implemented)
        permit_number: Optional DOB permit number for LL149 CS validation
        check_ll149: Whether to check for LL149 violations (default: True)
    
    Returns:
        Dict containing ComplianceResult and metadata
        Must include 'input_tokens' and 'output_tokens' for cost tracking
    """
    pdf_path_str = str(pdf_path)
    document_id = f"COI-{datetime.now().strftime('%Y%m%d')}-{hash(pdf_path_str) % 10000:04d}"
    
    # Load validation rules
    rules = _load_validation_rules()
    
    # STEP 1: OCR EXTRACTION
    ocr_result = _simulate_ocr(pdf_path_str)
    ocr_confidence = ocr_result["ocr_confidence"]
    page_count = ocr_result["page_count"]
    
    # Token usage for OCR + field extraction
    # PDF image: ~800 tokens per page, structured output: ~300 tokens
    input_tokens = page_count * 800 + 200  # Pages + system prompt
    output_tokens = 300  # Structured JSON response
    
    # BINDING CONSTRAINT: IF OCR confidence < 95%, RETURN status="ILLEGIBLE"
    if ocr_confidence < rules["minimum_ocr_confidence"]:
        # Create decision proof for illegible document
        logic_citations = [
            LogicCitation(
                standard=ComplianceStandard.NYC_RCNY_101_08,
                clause="Quality Standards",
                interpretation=f"Document quality insufficient for automated validation (confidence: {ocr_confidence:.1%})",
                confidence=ocr_confidence
            )
        ]
        
        decision_proof = create_decision_proof(
            agent_name="Guard",
            decision="ILLEGIBLE",
            input_data={
                "document_id": document_id,
                "pdf_path": pdf_path_str,
                "ocr_confidence": ocr_confidence,
                "page_count": page_count
            },
            logic_citations=logic_citations,
            reasoning=f"OCR confidence {ocr_confidence:.1%} is below required 95% threshold. Document requires manual review or re-scanning at higher quality.",
            confidence=ocr_confidence,
            risk_level="MEDIUM",
            estimated_financial_impact=None,
            cost_usd=0.0
        )
        
        result = ComplianceResult(
            status="ILLEGIBLE",
            deficiency_list=[f"OCR confidence {ocr_confidence:.1%} below 95% threshold"],
            decision_proof=decision_proof.proof_hash,
            confidence_score=ocr_confidence,
            processing_cost=0.0,  # Will be set by decorator
            document_id=document_id,
            ocr_confidence=ocr_confidence,
            page_count=page_count,
            citations=["OCR Quality Standards"]
        )
        
        return {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "result": result,
            "decision_proof_obj": decision_proof,
            "metadata": {
                "document_id": document_id,
                "success": False
            }
        }
    
    # STEP 2: FIELD EXTRACTION (Claude Haiku)
    extracted_fields = _parse_coi_fields(ocr_result["extracted_text"], pdf_path_str)
    
    # STEP 3: VALIDATION
    deficiencies = []
    citations = []
    logic_citations = []
    
    # Check Additional Insured
    if not extracted_fields["has_additional_insured"]:
        deficiency = "Missing Additional Insured endorsement"
        citation = rules["citations"]["additional_insured"]
        deficiencies.append(deficiency)
        citations.append(citation)
        logic_citations.append(
            LogicCitation(
                standard=ComplianceStandard.NYC_RCNY_101_08,
                clause="§101-08(c)(3)",
                interpretation="Certificate holder must be named as Additional Insured on General Liability policy",
                confidence=0.98
            )
        )
    
    # Check Waiver of Subrogation
    if not extracted_fields["has_waiver_of_subrogation"]:
        deficiency = "Missing Waiver of Subrogation"
        citation = rules["citations"]["waiver_of_subrogation"]
        deficiencies.append(deficiency)
        citations.append(citation)
        logic_citations.append(
            LogicCitation(
                standard=ComplianceStandard.WAIVER_SUBROGATION,
                clause="SCA Bulletin 2024-03",
                interpretation="Insurer must waive right to pursue certificate holder for claims (required for contracts >$1M)",
                confidence=0.95
            )
        )
    
    # Check GL Limits
    if extracted_fields["gl_per_occurrence"] < rules["minimum_gl_per_occurrence"]:
        deficiency = f"General Liability per occurrence ${extracted_fields['gl_per_occurrence']:,.0f} below minimum ${rules['minimum_gl_per_occurrence']:,.0f}"
        citation = rules["citations"]["minimum_limits"]
        deficiencies.append(deficiency)
        citations.append(citation)
        logic_citations.append(
            LogicCitation(
                standard=ComplianceStandard.ISO_GL_MINIMUM,
                clause="AIA A201-2017 §11.1",
                interpretation="Minimum General Liability coverage of $2M per occurrence required for NYC construction",
                confidence=0.99
            )
        )
    
    if extracted_fields["gl_aggregate"] < rules["minimum_gl_aggregate"]:
        deficiency = f"General Liability aggregate ${extracted_fields['gl_aggregate']:,.0f} below minimum ${rules['minimum_gl_aggregate']:,.0f}"
        citation = rules["citations"]["minimum_limits"]
        deficiencies.append(deficiency)
        citations.append(citation)
        if not any(c.standard == ComplianceStandard.ISO_GL_MINIMUM for c in logic_citations):
            logic_citations.append(
                LogicCitation(
                    standard=ComplianceStandard.ISO_GL_MINIMUM,
                    clause="AIA A201-2017 §11.1",
                    interpretation="Minimum General Liability aggregate of $4M required for NYC construction",
                    confidence=0.99
                )
            )
    
    # Check Expiration
    if extracted_fields["expiration_date"] < datetime.now():
        deficiency = f"Policy expired on {extracted_fields['expiration_date'].strftime('%Y-%m-%d')}"
        citation = rules["citations"]["expired_policy"]
        deficiencies.append(deficiency)
        citations.append(citation)
        logic_citations.append(
            LogicCitation(
                standard=ComplianceStandard.NYC_BC_3301,
                clause="§3301.9",
                interpretation="Insurance coverage must be current and unexpired during construction activities",
                confidence=0.99
            )
        )
    
    # 2026 UPGRADE: Check Local Law 149 (One-Job Rule) for Construction Superintendent
    ll149_violation = None
    if check_ll149 and permit_number:
        # Get CS info from permit
        cs_info = _get_permit_cs_info(permit_number)
        if cs_info:
            ll149_violation = _check_cs_ll149_compliance(
                permit_number=permit_number,
                cs_name=cs_info.get("cs_name"),
                cs_license=cs_info.get("cs_license")
            )
            
            if ll149_violation:
                # Add LL149 violation to deficiencies using explainability fields
                deficiency = (
                    f"[{ll149_violation.legal_basis}] {ll149_violation.explanation}"
                )
                citation = ll149_violation.legal_basis
                deficiencies.append(deficiency)
                citations.append(citation)
                logic_citations.append(
                    LogicCitation(
                        standard=ComplianceStandard.NYC_BC_3301,  # Using existing standard, ideally add LL149
                        clause="Local Law 149 §1 (The One-Job Rule)",
                        interpretation=ll149_violation.explanation,
                        confidence=0.99
                    )
                )
    
    # Add passing citations if compliant
    if not deficiencies:
        logic_citations.append(
            LogicCitation(
                standard=ComplianceStandard.NYC_RCNY_101_08,
                clause="§101-08(c)(3)",
                interpretation="All required endorsements present and coverage limits adequate",
                confidence=0.98
            )
        )
    
    # Determine status
    if not deficiencies:
        status = "APPROVED"
        confidence_score = 0.98
        risk_level = "LOW"
        estimated_financial_impact = 50_000  # Risk avoided
    else:
        status = "REJECTED"
        confidence_score = 0.92
        risk_level = "HIGH"
        estimated_financial_impact = -500_000  # Liability exposure
    
    # Build reasoning
    if status == "APPROVED":
        reasoning = (
            f"Certificate of Insurance {document_id} APPROVED. "
            f"All NYC construction insurance requirements satisfied: "
            f"Additional Insured ✓, Waiver of Subrogation ✓, "
            f"GL coverage ${extracted_fields['gl_per_occurrence']:,.0f}/${extracted_fields['gl_aggregate']:,.0f} ✓, "
            f"valid until {extracted_fields['expiration_date'].strftime('%Y-%m-%d')} ✓"
        )
    else:
        reasoning = (
            f"Certificate of Insurance {document_id} REJECTED. "
            f"Critical deficiencies found: {'; '.join(deficiencies)}. "
            f"Contractor must provide corrected COI before site access."
        )
    
    # STEP 4: GENERATE DECISION PROOF
    decision_proof = create_decision_proof(
        agent_name="Guard",
        decision=status,
        input_data={
            "document_id": document_id,
            "pdf_path": pdf_path_str,
            "ocr_confidence": ocr_confidence,
            "extracted_fields": {
                k: v.isoformat() if isinstance(v, datetime) else v
                for k, v in extracted_fields.items()
            }
        },
        logic_citations=logic_citations,
        reasoning=reasoning,
        confidence=confidence_score,
        risk_level=risk_level,
        estimated_financial_impact=estimated_financial_impact,
        cost_usd=0.0  # Will be filled by decorator
    )
    
    # Create ComplianceResult
    result = ComplianceResult(
        status=status,
        deficiency_list=deficiencies,
        decision_proof=decision_proof.proof_hash,
        confidence_score=confidence_score,
        processing_cost=0.0,  # Will be updated after decorator
        document_id=document_id,
        ocr_confidence=ocr_confidence,
        page_count=page_count,
        citations=citations
    )
    
    return_data = {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "result": result,
        "decision_proof_obj": decision_proof,
        "ll149_violation": ll149_violation,  # 2026 UPGRADE: Include LL149 violation if detected
        "metadata": {
            "document_id": document_id,
            "success": status == "APPROVED",
            "permit_number": permit_number  # Include permit for traceability
        }
    }
    
    # Note: The decorator will add cost_usd to this dict
    # We need to update the result object after the decorator runs
    return return_data
