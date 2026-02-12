"""
Safety Plan Forgery Detector - AI Detection of Forged PE Stamps

Detects forged Professional Engineer stamps on safety plans to prevent
submission of fraudulent documents to DOB. Features:
- PE stamp authenticity verification
- DOB-approved plan database cross-reference  
- Metadata inconsistency detection
- Logo quality analysis (pixelation = cut/paste)
- Date pattern anomaly detection

VALUE PROPOSITION: "This safety plan is forged. Do not submit."

Version: 2026.1.0
Last Updated: 2026-02-12
"""
from typing import Dict, List, Optional, Literal, Tuple
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
import re
import hashlib


# =============================================================================
# CONSTANTS - PE STAMP REQUIREMENTS
# =============================================================================

# Valid PE license format
PE_LICENSE_PATTERN = r"PE[- ]?\d{6}"  # PE-123456 or PE 123456

# Required elements on PE stamp
REQUIRED_STAMP_ELEMENTS = [
    "professional_engineer",
    "license_number",
    "state",
    "seal_or_stamp"
]

# NYC PE license database (mock - in production: query actual DOB database)
VALID_PE_LICENSES = {
    "PE-123456": {"name": "John Smith", "status": "active", "discipline": "Structural"},
    "PE-234567": {"name": "Jane Doe", "status": "active", "discipline": "Mechanical"},
    "PE-345678": {"name": "Bob Johnson", "status": "active", "discipline": "Civil"},
}

# Forgery indicators
FORGERY_INDICATORS = {
    "pixelated_stamp": "PE stamp is low resolution (cut/paste from another document)",
    "invalid_license": "PE license number not found in DOB database",
    "expired_license": "PE license has expired or been revoked",
    "mismatched_name": "PE name doesn't match license database",
    "weekend_filing": "Plan signed on weekend (unusual for PE)",
    "metadata_mismatch": "Document metadata doesn't match stated date",
    "duplicate_stamp": "Exact same stamp image used on multiple plans",
    "wrong_discipline": "PE discipline doesn't match plan type",
    "missing_elements": "PE stamp missing required elements",
    "font_inconsistency": "PE stamp uses inconsistent or wrong fonts"
}

# Standard safety plan sections
REQUIRED_PLAN_SECTIONS = [
    "site_safety_manager",
    "emergency_procedures",
    "fall_protection",
    "scaffold_requirements",
    "excavation_safety",
    "crane_operations"
]


# =============================================================================
# PYDANTIC MODELS
# =============================================================================

class PEStampData(BaseModel):
    """Extracted PE stamp data"""
    model_config = ConfigDict(frozen=True)
    
    license_number: Optional[str] = Field(default=None, description="PE license number")
    engineer_name: Optional[str] = Field(default=None, description="Engineer name on stamp")
    state: str = Field(default="NY", description="State of license")
    discipline: Optional[str] = Field(default=None, description="Engineering discipline")
    
    stamp_present: bool = Field(description="PE stamp detected")
    stamp_quality: Literal["high", "medium", "low"] = Field(
        default="medium",
        description="Visual quality of stamp"
    )
    stamp_location: Optional[str] = Field(default=None, description="Page/section where stamp found")


class DocumentMetadata(BaseModel):
    """Document metadata analysis"""
    model_config = ConfigDict(frozen=True)
    
    creation_date: Optional[datetime] = Field(default=None, description="File creation date")
    modification_date: Optional[datetime] = Field(default=None, description="Last modified date")
    author: Optional[str] = Field(default=None, description="Document author")
    software: Optional[str] = Field(default=None, description="Software used to create")
    
    stated_date: Optional[datetime] = Field(default=None, description="Date stated on document")
    signed_date: Optional[datetime] = Field(default=None, description="Signature date")
    
    metadata_consistent: bool = Field(description="Metadata matches stated dates")
    anomalies: List[str] = Field(default_factory=list, description="Metadata anomalies detected")


class SafetyPlanData(BaseModel):
    """Extracted safety plan data"""
    model_config = ConfigDict(frozen=False)
    
    # Document identification
    plan_id: str = Field(description="Safety plan identifier")
    project_address: Optional[str] = Field(default=None, description="Project site address")
    job_number: Optional[str] = Field(default=None, description="DOB job number")
    
    # PE information
    pe_stamp: Optional[PEStampData] = Field(default=None, description="PE stamp data")
    
    # Safety manager
    safety_manager_name: Optional[str] = Field(default=None, description="Site safety manager")
    safety_manager_cert: Optional[str] = Field(default=None, description="Safety cert number")
    
    # Plan sections
    sections_present: List[str] = Field(default_factory=list, description="Safety sections found")
    sections_completeness: float = Field(
        ge=0.0, le=1.0,
        description="Percentage of required sections"
    )
    
    # Metadata
    document_metadata: Optional[DocumentMetadata] = Field(default=None)
    
    # Dates
    plan_date: Optional[datetime] = Field(default=None, description="Plan preparation date")
    expiration_date: Optional[datetime] = Field(default=None, description="Plan expiration")


class ForgeryDetectionResult(BaseModel):
    """PE stamp forgery detection result"""
    model_config = ConfigDict(frozen=False)
    
    plan_id: str = Field(description="Safety plan ID")
    
    # Overall assessment
    is_forged: bool = Field(description="Plan flagged as forged")
    forgery_probability: float = Field(
        ge=0.0, le=1.0,
        description="Forgery probability (0-1)"
    )
    confidence: float = Field(
        ge=0.0, le=1.0,
        description="Detection confidence (0-1)"
    )
    
    # Forgery indicators
    forgery_indicators: List[str] = Field(default_factory=list, description="Forgery indicators found")
    forgery_details: Dict[str, str] = Field(default_factory=dict, description="Detailed findings")
    
    # Verification checks
    pe_license_valid: bool = Field(description="PE license is valid")
    pe_name_matches: bool = Field(description="PE name matches database")
    stamp_quality_acceptable: bool = Field(description="Stamp quality is acceptable")
    metadata_consistent: bool = Field(description="Metadata is consistent")
    plan_completeness_acceptable: bool = Field(description="Plan has required sections")
    
    # Risk assessment
    submission_risk: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] = Field(
        description="Risk of submitting this plan"
    )
    recommended_action: str = Field(description="Recommended action")
    
    # Legal implications
    potential_penalties: str = Field(description="Potential DOB penalties if submitted")
    
    # Analysis metadata
    analysis_timestamp: datetime = Field(default_factory=datetime.utcnow)
    analysis_hash: str = Field(description="SHA-256 hash of analysis")


class PEStampComparison(BaseModel):
    """Comparison of PE stamps across multiple plans"""
    model_config = ConfigDict(frozen=True)
    
    pe_license: str = Field(description="PE license being compared")
    plan_count: int = Field(description="Number of plans reviewed")
    
    stamp_consistency: float = Field(
        ge=0.0, le=1.0,
        description="Consistency of stamp appearance (0-1)"
    )
    
    duplicate_detected: bool = Field(description="Exact duplicate stamp images found")
    suspicious_patterns: List[str] = Field(default_factory=list, description="Suspicious patterns")


# =============================================================================
# SAFETY PLAN FORGERY DETECTOR
# =============================================================================

class SafetyPlanForgeryDetector:
    """
    AI-Powered Safety Plan Forgery Detection
    
    Detects forged PE stamps and fraudulent safety plans to prevent
    submission of non-compliant documents to DOB.
    """
    
    def __init__(self):
        """Initialize detector"""
        self.verified_plans: Dict[str, SafetyPlanData] = {}
        self.pe_stamp_database: Dict[str, List[str]] = {}  # PE license -> list of stamp hashes
    
    def extract_plan_data(
        self,
        document_text: str,
        plan_id: Optional[str] = None
    ) -> SafetyPlanData:
        """
        Extract structured data from safety plan
        
        Args:
            document_text: Raw OCR text from safety plan
            plan_id: Optional plan identifier
        
        Returns:
            SafetyPlanData object
        """
        if plan_id is None:
            plan_id = f"SP-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Extract PE stamp information
        pe_stamp = self._extract_pe_stamp(document_text)
        
        # Extract project information
        project_address = self._extract_field(
            document_text,
            ["project location:", "site address:", "address:"]
        )
        job_number = self._extract_field(
            document_text,
            ["job number:", "dob job #:", "job #:"]
        )
        
        # Extract safety manager
        safety_manager = self._extract_field(
            document_text,
            ["site safety manager:", "safety manager:", "ssm:"]
        )
        
        # Check for required sections
        sections_present = []
        for section in REQUIRED_PLAN_SECTIONS:
            if section.replace("_", " ") in document_text.lower():
                sections_present.append(section)
        
        sections_completeness = len(sections_present) / len(REQUIRED_PLAN_SECTIONS)
        
        # Extract dates
        plan_date = self._extract_date(document_text, ["prepared:", "date:", "plan date:"])
        
        return SafetyPlanData(
            plan_id=plan_id,
            project_address=project_address,
            job_number=job_number,
            pe_stamp=pe_stamp,
            safety_manager_name=safety_manager,
            sections_present=sections_present,
            sections_completeness=sections_completeness,
            plan_date=plan_date
        )
    
    def detect_forgery(
        self,
        plan_data: SafetyPlanData,
        document_text: str,
        document_metadata: Optional[DocumentMetadata] = None,
        previous_plans: Optional[List[SafetyPlanData]] = None
    ) -> ForgeryDetectionResult:
        """
        Detect forged PE stamps and fraudulent plans
        
        Args:
            plan_data: Extracted safety plan data
            document_text: Raw document text
            document_metadata: Document metadata (if available)
            previous_plans: Previous plans from same PE (for comparison)
        
        Returns:
            ForgeryDetectionResult object
        """
        forgery_indicators = []
        forgery_details = {}
        forgery_score = 0.0
        
        # Check 1: PE license validation
        pe_license_valid = False
        pe_name_matches = True
        
        if plan_data.pe_stamp and plan_data.pe_stamp.license_number:
            license_num = plan_data.pe_stamp.license_number
            
            # Check if license exists in database
            if license_num in VALID_PE_LICENSES:
                pe_license_valid = True
                
                # Check if name matches
                db_name = VALID_PE_LICENSES[license_num]["name"]
                if plan_data.pe_stamp.engineer_name:
                    # Simple name matching (in production: fuzzy matching)
                    if db_name.lower() not in plan_data.pe_stamp.engineer_name.lower():
                        pe_name_matches = False
                        forgery_indicators.append("mismatched_name")
                        forgery_details["mismatched_name"] = (
                            f"Stamp shows '{plan_data.pe_stamp.engineer_name}' but "
                            f"database shows '{db_name}'"
                        )
                        forgery_score += 0.4
            else:
                forgery_indicators.append("invalid_license")
                forgery_details["invalid_license"] = (
                    f"PE license {license_num} not found in DOB database"
                )
                forgery_score += 0.5
        else:
            forgery_indicators.append("missing_elements")
            forgery_details["missing_elements"] = "PE stamp or license number missing"
            forgery_score += 0.3
        
        # Check 2: Stamp quality
        stamp_quality_acceptable = True
        if plan_data.pe_stamp:
            if plan_data.pe_stamp.stamp_quality == "low":
                forgery_indicators.append("pixelated_stamp")
                forgery_details["pixelated_stamp"] = (
                    "PE stamp is low resolution, suggests cut/paste from another document"
                )
                forgery_score += 0.35
                stamp_quality_acceptable = False
        
        # Check 3: Metadata consistency
        metadata_consistent = True
        if document_metadata:
            if not document_metadata.metadata_consistent:
                forgery_indicators.append("metadata_mismatch")
                forgery_details["metadata_mismatch"] = (
                    f"File dates don't match stated plan date. "
                    f"Anomalies: {', '.join(document_metadata.anomalies)}"
                )
                forgery_score += 0.25
                metadata_consistent = False
        
        # Check 4: Weekend filing (suspicious pattern)
        if plan_data.plan_date:
            if plan_data.plan_date.weekday() in [5, 6]:  # Saturday or Sunday
                forgery_indicators.append("weekend_filing")
                forgery_details["weekend_filing"] = (
                    f"Plan dated {plan_data.plan_date.strftime('%A, %B %d, %Y')} (weekend). "
                    "Most PE stamps are applied on weekdays."
                )
                forgery_score += 0.15
        
        # Check 5: Plan completeness
        plan_completeness_acceptable = plan_data.sections_completeness >= 0.7
        if not plan_completeness_acceptable:
            forgery_indicators.append("incomplete_plan")
            forgery_details["incomplete_plan"] = (
                f"Only {plan_data.sections_completeness:.0%} of required safety sections present. "
                "Legitimate PE stamps typically appear on complete plans."
            )
            forgery_score += 0.2
        
        # Check 6: Duplicate stamp detection
        if previous_plans and plan_data.pe_stamp:
            # In production: compare actual stamp images
            # For now: check if exact same license appears suspiciously often
            same_pe_count = sum(
                1 for p in previous_plans 
                if p.pe_stamp and p.pe_stamp.license_number == plan_data.pe_stamp.license_number
            )
            if same_pe_count > 20:  # More than 20 plans with same stamp
                forgery_indicators.append("duplicate_stamp")
                forgery_details["duplicate_stamp"] = (
                    f"This PE stamp appears on {same_pe_count} plans. "
                    "High volume suggests possible stamp reuse."
                )
                forgery_score += 0.2
        
        # Determine forgery probability and status
        forgery_probability = min(1.0, forgery_score)
        is_forged = forgery_probability >= 0.5  # 50% threshold
        confidence = 0.85  # Base confidence (ML model confidence in production)
        
        # Determine submission risk
        if forgery_probability >= 0.7:
            submission_risk = "CRITICAL"
        elif forgery_probability >= 0.5:
            submission_risk = "HIGH"
        elif forgery_probability >= 0.3:
            submission_risk = "MEDIUM"
        else:
            submission_risk = "LOW"
        
        # Recommended action
        if is_forged:
            recommended_action = (
                "DO NOT SUBMIT: This safety plan appears forged. "
                "Contact the PE directly to verify authenticity before submission. "
                "Submitting a forged plan is a Class E felony (NYC Admin Code §28-208.1)."
            )
            potential_penalties = (
                "Submitting forged documents: $25,000 fine + up to 4 years imprisonment. "
                "PE license revocation. Project stop work order."
            )
        elif forgery_probability >= 0.3:
            recommended_action = (
                "VERIFY: Contact PE to confirm they stamped this plan before submitting."
            )
            potential_penalties = (
                "If forged and submitted: Criminal penalties + civil fines. "
                "Recommend verification before submission."
            )
        else:
            recommended_action = "PROCEED: Plan appears authentic. Safe to submit."
            potential_penalties = "None identified."
        
        # Create analysis hash
        analysis_data = {
            "plan_id": plan_data.plan_id,
            "timestamp": datetime.utcnow().isoformat(),
            "forgery_score": forgery_score,
            "indicators": forgery_indicators
        }
        analysis_hash = hashlib.sha256(
            str(analysis_data).encode()
        ).hexdigest()
        
        return ForgeryDetectionResult(
            plan_id=plan_data.plan_id,
            is_forged=is_forged,
            forgery_probability=forgery_probability,
            confidence=confidence,
            forgery_indicators=forgery_indicators,
            forgery_details=forgery_details,
            pe_license_valid=pe_license_valid,
            pe_name_matches=pe_name_matches,
            stamp_quality_acceptable=stamp_quality_acceptable,
            metadata_consistent=metadata_consistent,
            plan_completeness_acceptable=plan_completeness_acceptable,
            submission_risk=submission_risk,
            recommended_action=recommended_action,
            potential_penalties=potential_penalties,
            analysis_hash=analysis_hash
        )
    
    def _extract_pe_stamp(self, text: str) -> Optional[PEStampData]:
        """Extract PE stamp information"""
        # Extract PE license number
        license_match = re.search(PE_LICENSE_PATTERN, text, re.IGNORECASE)
        license_num = license_match.group(0) if license_match else None
        
        # Extract engineer name (look for "P.E." or "Professional Engineer")
        name_pattern = r"([A-Z][a-z]+(?:\s+[A-Z]\.?)?\s+[A-Z][a-z]+),?\s+P\.?E\.?"
        name_match = re.search(name_pattern, text)
        engineer_name = name_match.group(1) if name_match else None
        
        # Check if stamp is present
        stamp_keywords = ["professional engineer", "p.e.", "seal", "stamp"]
        stamp_present = any(kw in text.lower() for kw in stamp_keywords)
        
        # Assess stamp quality (simplified - in production: image analysis)
        # Look for indicators of low quality
        if "scan" in text.lower() or "copy" in text.lower():
            stamp_quality = "low"
        elif stamp_present and license_num:
            stamp_quality = "high"
        else:
            stamp_quality = "medium"
        
        if stamp_present or license_num:
            return PEStampData(
                license_number=license_num,
                engineer_name=engineer_name,
                state="NY",
                stamp_present=stamp_present,
                stamp_quality=stamp_quality
            )
        
        return None
    
    def _extract_field(self, text: str, labels: List[str]) -> Optional[str]:
        """Extract field value after label"""
        for label in labels:
            pattern = rf"{re.escape(label)}\s*(.+?)(?:\n|$)"
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None
    
    def _extract_date(self, text: str, labels: List[str]) -> Optional[datetime]:
        """Extract date after label"""
        for label in labels:
            pattern = rf"{re.escape(label)}\s*(\d{{1,2}}[/-]\d{{1,2}}[/-]\d{{2,4}})"
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                date_str = match.group(1)
                try:
                    for fmt in ["%m/%d/%Y", "%m-%d-%Y", "%m/%d/%y"]:
                        try:
                            return datetime.strptime(date_str, fmt)
                        except ValueError:
                            continue
                except Exception:
                    pass
        return None


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def quick_forgery_check(document_text: str) -> Dict[str, Any]:
    """
    Quick safety plan forgery check
    
    VALUE PROPOSITION: "This safety plan is forged. Do not submit."
    
    Args:
        document_text: Raw safety plan text
    
    Returns:
        Dict with forgery assessment
    """
    detector = SafetyPlanForgeryDetector()
    
    # Extract data
    plan_data = detector.extract_plan_data(document_text)
    
    # Detect forgery
    forgery_result = detector.detect_forgery(plan_data, document_text)
    
    return {
        "plan_id": plan_data.plan_id,
        "pe_license": plan_data.pe_stamp.license_number if plan_data.pe_stamp else None,
        "is_forged": forgery_result.is_forged,
        "forgery_probability": forgery_result.forgery_probability,
        "forgery_indicators": forgery_result.forgery_indicators,
        "submission_risk": forgery_result.submission_risk,
        "recommended_action": forgery_result.recommended_action,
        "potential_penalties": forgery_result.potential_penalties,
        "plan_completeness": plan_data.sections_completeness
    }
