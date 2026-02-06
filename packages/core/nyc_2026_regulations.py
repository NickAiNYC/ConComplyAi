"""
NYC 2026 Mandate Regulations - Centralized Constants and Helpers

This module consolidates all 2026 NYC regulatory logic including:
- Local Law 149 (The One-Job Rule) - Construction Superintendent restrictions
- Local Law 152 (Gas Piping) - GPS2 certification requirements

All LL149 and LL152 checks use shared constants from this module to ensure
consistency across Scout, Guard, and Fixer agents.

Version: 2026.1.0
Last Updated: 2026-02-06
"""
from typing import Dict, List, Optional, Literal, Any
from datetime import datetime
from pydantic import BaseModel, Field


# =============================================================================
# LOCAL LAW 149 - THE ONE-JOB RULE
# =============================================================================

LL149_RULE_NAME = "Local Law 149 of 2026 (The One-Job Rule)"
LL149_SHORT_CODE = "LL149"
LL149_CITATION = "NYC Local Law 149 §1 - Construction Superintendent Designation"
LL149_EFFECTIVE_DATE = datetime(2026, 1, 1)

# Maximum number of active Primary CS designations allowed per superintendent
LL149_MAX_PRIMARY_DESIGNATIONS = 1

# Explanation template
LL149_EXPLANATION_TEMPLATE = (
    "Construction Superintendent {cs_name} is designated as Primary on {active_count} "
    "active permits. NYC Local Law 149 limits each CS to ONE primary designation to "
    "ensure adequate on-site supervision and prevent CS over-extension."
)

# Suggested actions
LL149_SUGGESTED_ACTIONS = {
    "multiple_primary": "Reassign superintendent or close out prior permit to satisfy one-job rule.",
    "designation_conflict": "Designate backup CS as primary on one project, or hire additional CS.",
    "compliance_check": "Verify CS designations across all active permits in BIS system."
}


class LL149Finding(BaseModel):
    """
    Structured finding for Local Law 149 violations
    Includes explainability fields for transparency
    """
    # Core identification
    cs_name: str = Field(description="Construction Superintendent full name")
    cs_license_number: str = Field(description="NYC CS License Number")
    active_primary_permits: List[str] = Field(
        description="List of permit numbers where CS is designated as Primary"
    )
    
    # Explainability fields (2026 requirement)
    legal_basis: str = Field(
        default=f"{LL149_SHORT_CODE} - {LL149_RULE_NAME}",
        description="Short code + citation string"
    )
    explanation: str = Field(
        description="1-2 human sentences describing why this was flagged"
    )
    suggested_action: str = Field(
        description="One concise directive for remediation"
    )
    
    # Severity
    severity: Literal["HIGH_RISK_MANDATE", "MEDIUM", "LOW"] = Field(
        default="HIGH_RISK_MANDATE"
    )
    
    # Metadata
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    regulation_version: str = Field(default="2026.1.0")
    
    class Config:
        frozen = True


def is_ll149_superintendent_conflict(
    cs_license_number: str,
    active_permits: List[Dict[str, Any]],
    cs_name: Optional[str] = None
) -> Optional[LL149Finding]:
    """
    Check if Construction Superintendent violates Local Law 149 (One-Job Rule)
    
    NYC Local Law 149 (2024, effective 2026) restricts Construction Superintendents
    to ONE active Primary designation to ensure adequate on-site supervision.
    
    CONTIGUOUS-LOT EXCEPTION (RCNY §101-08):
    Legitimate multi-site superintendent coverage for contiguous lots is not flagged
    as a violation, per NYC Rules. This implementation currently detects raw >1 job
    conflicts; external systems should apply contiguous-lot logic before escalation.
    
    This is a centralized helper used by Guard, Scout, and integration tests.
    
    Args:
        cs_license_number: NYC CS License Number (e.g., "CS-123456")
        active_permits: List of dicts with keys: permit_number, designation, is_active
        cs_name: Optional CS name for reporting
    
    Returns:
        LL149Finding if violation detected, None if compliant
    
    Example:
        >>> active_permits = [
        ...     {"permit_number": "121234567", "designation": "Primary", "is_active": True},
        ...     {"permit_number": "121234568", "designation": "Primary", "is_active": True},
        ... ]
        >>> finding = is_ll149_superintendent_conflict("CS-123456", active_permits, "John Smith")
        >>> assert finding.severity == "HIGH_RISK_MANDATE"
    """
    # Count Primary designations on active permits
    primary_count = sum(
        1 for permit in active_permits
        if permit.get("designation") == "Primary" and permit.get("is_active", False)
    )
    
    # Check if exceeds limit
    if primary_count > LL149_MAX_PRIMARY_DESIGNATIONS:
        # Extract permit numbers
        primary_permits = [
            permit["permit_number"] for permit in active_permits
            if permit.get("designation") == "Primary" and permit.get("is_active", False)
        ]
        
        # Generate explanation
        explanation = LL149_EXPLANATION_TEMPLATE.format(
            cs_name=cs_name or cs_license_number,
            active_count=primary_count
        )
        
        # Create finding
        return LL149Finding(
            cs_name=cs_name or "Unknown CS",
            cs_license_number=cs_license_number,
            active_primary_permits=primary_permits,
            legal_basis=f"{LL149_SHORT_CODE} - {LL149_RULE_NAME}",
            explanation=explanation,
            suggested_action=LL149_SUGGESTED_ACTIONS["multiple_primary"],
            severity="HIGH_RISK_MANDATE"
        )
    
    return None


# =============================================================================
# LOCAL LAW 152 - GAS PIPING SYSTEM
# =============================================================================

LL152_RULE_NAME = "Local Law 152 of 2016 (Gas Piping System Periodic Inspection)"
LL152_SHORT_CODE = "LL152"
LL152_CITATION = "NYC Local Law 152 §28-318.3 - GPS2 Certification"
LL152_EFFECTIVE_DATE = datetime(2016, 7, 1)

# 2026 due-cycle Community Districts
LL152_2026_DUE_CYCLE_DISTRICTS = [4, 6, 8, 9, 16]

# Fine amounts
LL152_BASE_FINE = 10000.0  # $10,000 base fine
LL152_PENALTY = LL152_BASE_FINE  # Alias for consistency
LL152_DAILY_PENALTY = 250.0  # $250 per day after deadline

# Estimated costs
LL152_INSPECTION_COST_MIN = 2000.0
LL152_INSPECTION_COST_MAX = 3000.0
LL152_INSPECTION_COST_TYPICAL = 2500.0

# Deadline for 2026 cycle
LL152_2026_DEADLINE = datetime(2026, 12, 31, 23, 59, 59)

# Explanation templates
LL152_EXPLANATION_TEMPLATE = (
    "Building {bin} in Community District {cd} is in the 2026 LL152 due-cycle. "
    "GPS2 gas piping inspection certification is {status}. "
    "Failure to file by {deadline} results in ${fine:,.0f} fine plus daily penalties."
)

# Suggested actions
LL152_SUGGESTED_ACTIONS = {
    "missing_gps2": "Hire Licensed Master Plumber (LMP) to conduct GPS2 inspection and file certification with DOB.",
    "approaching_deadline": "Expedite GPS2 filing - deadline approaching. Fine: $10,000 + $250/day.",
    "not_in_cycle": "Building not in 2026 due-cycle. Monitor for future cycles."
}


class LL152Finding(BaseModel):
    """
    Structured finding for Local Law 152 GPS2 requirements
    Includes explainability fields for transparency
    """
    # Core identification
    building_bin: str = Field(description="NYC Building Identification Number")
    building_address: str = Field(description="Full building address")
    community_district: int = Field(ge=1, le=59, description="NYC Community District")
    
    # GPS2 status
    has_gps2_certification: bool = Field(
        description="Whether GPS2 is on file with DOB"
    )
    certification_date: Optional[datetime] = Field(
        default=None,
        description="Date GPS2 was filed (if available)"
    )
    in_2026_due_cycle: bool = Field(
        description="Whether building is in 2026 due cycle"
    )
    
    # Explainability fields (2026 requirement)
    legal_basis: str = Field(
        default=f"{LL152_SHORT_CODE} - {LL152_RULE_NAME}",
        description="Short code + citation string"
    )
    explanation: str = Field(
        description="1-2 human sentences describing filing requirement"
    )
    suggested_action: str = Field(
        description="One concise directive for remediation"
    )
    
    # Financial impact
    projected_fine: float = Field(
        default=LL152_BASE_FINE,
        description="Fine amount for non-compliance"
    )
    estimated_filing_cost: float = Field(
        default=LL152_INSPECTION_COST_TYPICAL,
        description="Estimated cost for GPS2 inspection and filing"
    )
    
    # Deadline
    deadline: datetime = Field(
        default=LL152_2026_DEADLINE,
        description="Compliance deadline"
    )
    
    # Severity
    severity: Literal["HIGH", "MEDIUM", "LOW"] = Field(
        default="HIGH",
        description="Finding severity"
    )
    
    # Metadata
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    regulation_version: str = Field(default="2026.1.0")
    
    class Config:
        frozen = True


def needs_ll152_gps2_remediation(
    building_bin: str,
    building_address: str,
    community_district: int,
    has_gps2_certification: bool = False,
    certification_date: Optional[datetime] = None,
    current_year: int = 2026
) -> Optional[LL152Finding]:
    """
    Check if building needs Local Law 152 GPS2 remediation
    
    This is a centralized helper used by Fixer, Scout, and integration tests.
    
    Args:
        building_bin: NYC Building Identification Number
        building_address: Full building address
        community_district: NYC Community District (1-59)
        has_gps2_certification: Whether GPS2 is on file
        certification_date: Date GPS2 was filed (if available)
        current_year: Current year for cycle determination (default: 2026)
    
    Returns:
        LL152Finding if remediation needed, None if compliant or not in cycle
    
    Example:
        >>> finding = needs_ll152_gps2_remediation(
        ...     building_bin="1234567",
        ...     building_address="123 Main St, Manhattan",
        ...     community_district=4,
        ...     has_gps2_certification=False
        ... )
        >>> assert finding.in_2026_due_cycle == True
        >>> assert finding.projected_fine == 10000.0
    """
    # Check if in 2026 due-cycle
    in_due_cycle = (
        current_year == 2026 and
        community_district in LL152_2026_DUE_CYCLE_DISTRICTS
    )
    
    if not in_due_cycle:
        # Not in current cycle, no remediation needed
        return None
    
    if has_gps2_certification:
        # Already compliant, no remediation needed
        return None
    
    # Building is in cycle and missing GPS2 - needs remediation
    status = "MISSING" if not has_gps2_certification else "on file"
    
    explanation = LL152_EXPLANATION_TEMPLATE.format(
        bin=building_bin,
        cd=community_district,
        status=status,
        deadline=LL152_2026_DEADLINE.strftime("%B %d, %Y"),
        fine=LL152_BASE_FINE
    )
    
    return LL152Finding(
        building_bin=building_bin,
        building_address=building_address,
        community_district=community_district,
        has_gps2_certification=has_gps2_certification,
        certification_date=certification_date,
        in_2026_due_cycle=True,
        legal_basis=f"{LL152_SHORT_CODE} - {LL152_RULE_NAME}",
        explanation=explanation,
        suggested_action=LL152_SUGGESTED_ACTIONS["missing_gps2"],
        projected_fine=LL152_BASE_FINE,
        estimated_filing_cost=LL152_INSPECTION_COST_TYPICAL,
        deadline=LL152_2026_DEADLINE,
        severity="HIGH"
    )


# =============================================================================
# SHARED UTILITIES
# =============================================================================

def get_regulation_info(regulation_code: str) -> Dict[str, Any]:
    """
    Get regulation metadata by short code
    
    Args:
        regulation_code: LL149 or LL152
    
    Returns:
        Dict with rule_name, citation, effective_date, etc.
    """
    regulations = {
        "LL149": {
            "rule_name": LL149_RULE_NAME,
            "short_code": LL149_SHORT_CODE,
            "citation": LL149_CITATION,
            "effective_date": LL149_EFFECTIVE_DATE,
            "max_primary_designations": LL149_MAX_PRIMARY_DESIGNATIONS,
        },
        "LL152": {
            "rule_name": LL152_RULE_NAME,
            "short_code": LL152_SHORT_CODE,
            "citation": LL152_CITATION,
            "effective_date": LL152_EFFECTIVE_DATE,
            "due_cycle_districts": LL152_2026_DUE_CYCLE_DISTRICTS,
            "base_fine": LL152_BASE_FINE,
            "daily_penalty": LL152_DAILY_PENALTY,
        }
    }
    
    return regulations.get(regulation_code, {})


def format_legal_basis(regulation_code: str) -> str:
    """
    Format legal basis string for mandate findings
    
    Args:
        regulation_code: LL149 or LL152
    
    Returns:
        Formatted legal basis string
    """
    info = get_regulation_info(regulation_code)
    if not info:
        return f"{regulation_code} - Unknown Regulation"
    
    return f"{info['short_code']} - {info['rule_name']}"
