"""
Governance-as-Code Module
Safety guardrails to prevent unauthorized agent actions

Following 2026 Construction Tech compliance standards
"""
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class ReadyToSendStatus(str, Enum):
    """Status checks before agent can send outreach"""
    PENDING_VALIDATION = "PENDING_VALIDATION"
    MISSING_CONTACT_INFO = "MISSING_CONTACT_INFO"
    INVALID_ENDORSEMENT_LIST = "INVALID_ENDORSEMENT_LIST"
    SAFETY_HOLD = "SAFETY_HOLD"  # Manual override needed
    APPROVED = "APPROVED"  # Ready to send
    SENT = "SENT"  # Already sent


class SafetyGuardrail(BaseModel):
    """
    Safety check result
    Hardcoded rules prevent agents from taking unsafe actions
    """
    check_name: str
    passed: bool
    reason: Optional[str] = None
    requires_human_approval: bool = Field(default=False)


class OutreachValidation(BaseModel):
    """
    Validation result for outreach request
    Must pass all guardrails before sending
    """
    status: ReadyToSendStatus
    guardrails: List[SafetyGuardrail]
    can_send: bool = Field(default=False)
    blocking_issues: List[str] = Field(default_factory=list)
    approved_by: Optional[str] = None
    approval_timestamp: Optional[datetime] = None


def validate_ready_to_send(
    document_id: str,
    broker_contact: Any,  # BrokerContact
    missing_endorsements: List[str],
    validation_confidence: float,
    contractor_history: Optional[Dict[str, Any]] = None
) -> OutreachValidation:
    """
    Governance-as-Code validation for outreach
    
    Hardcoded safety guardrails:
    1. Must have valid broker contact (email OR phone)
    2. Must have specific endorsements listed (not generic)
    3. Must meet confidence threshold (>= 0.85)
    4. Cannot send if contractor is blacklisted
    5. Cannot send duplicate within 24 hours
    
    Returns OutreachValidation with APPROVED status only if all pass
    """
    guardrails = []
    blocking_issues = []
    
    # Guardrail 1: Valid contact information
    contact_check = SafetyGuardrail(
        check_name="valid_broker_contact",
        passed=False
    )
    
    if broker_contact and hasattr(broker_contact, 'has_valid_contact'):
        if broker_contact.has_valid_contact():
            contact_check.passed = True
            contact_check.reason = "Valid email or phone found"
        else:
            contact_check.reason = "No valid email or phone number"
            blocking_issues.append("Missing valid broker contact information")
    else:
        contact_check.reason = "Broker contact not provided"
        blocking_issues.append("Broker contact required for outreach")
    
    guardrails.append(contact_check)
    
    # Guardrail 2: Specific endorsements listed
    endorsement_check = SafetyGuardrail(
        check_name="specific_endorsements",
        passed=False
    )
    
    if missing_endorsements and len(missing_endorsements) > 0:
        # Check for specificity (not generic)
        generic_terms = ['missing', 'incomplete', 'invalid', 'error']
        is_specific = all(
            not any(term in end.lower() for term in generic_terms)
            for end in missing_endorsements
        )
        
        if is_specific:
            endorsement_check.passed = True
            endorsement_check.reason = f"Specific endorsements: {', '.join(missing_endorsements)}"
        else:
            endorsement_check.reason = "Endorsements too generic"
            blocking_issues.append("Missing endorsements must be specific (e.g., 'Waiver of Subrogation')")
    else:
        endorsement_check.reason = "No missing endorsements specified"
        blocking_issues.append("Must specify which endorsements are missing")
    
    guardrails.append(endorsement_check)
    
    # Guardrail 3: Confidence threshold
    confidence_check = SafetyGuardrail(
        check_name="confidence_threshold",
        passed=validation_confidence >= 0.85
    )
    
    if confidence_check.passed:
        confidence_check.reason = f"Confidence {validation_confidence:.2f} meets threshold"
    else:
        confidence_check.reason = f"Confidence {validation_confidence:.2f} below 0.85 threshold"
        blocking_issues.append("Validation confidence too low - requires human review")
        confidence_check.requires_human_approval = True
    
    guardrails.append(confidence_check)
    
    # Guardrail 4: Contractor blacklist check
    blacklist_check = SafetyGuardrail(
        check_name="contractor_blacklist",
        passed=True  # Default pass
    )
    
    if contractor_history:
        is_blacklisted = contractor_history.get('blacklisted', False)
        if is_blacklisted:
            blacklist_check.passed = False
            blacklist_check.reason = "Contractor is blacklisted"
            blacklist_check.requires_human_approval = True
            blocking_issues.append("Contractor blacklisted - requires management approval")
        else:
            blacklist_check.reason = "Contractor in good standing"
    else:
        blacklist_check.reason = "No history check performed"
    
    guardrails.append(blacklist_check)
    
    # Guardrail 5: Duplicate prevention (24hr window)
    duplicate_check = SafetyGuardrail(
        check_name="duplicate_prevention",
        passed=True  # Default pass (check implementation)
    )
    
    if contractor_history:
        last_outreach = contractor_history.get('last_outreach_timestamp')
        if last_outreach:
            hours_since = (datetime.now() - last_outreach).total_seconds() / 3600
            if hours_since < 24:
                duplicate_check.passed = False
                duplicate_check.reason = f"Last outreach was {hours_since:.1f} hours ago"
                blocking_issues.append("Cannot send duplicate outreach within 24 hours")
            else:
                duplicate_check.reason = f"Last outreach was {hours_since:.1f} hours ago (OK)"
        else:
            duplicate_check.reason = "No previous outreach found"
    else:
        duplicate_check.reason = "No history available for duplicate check"
    
    guardrails.append(duplicate_check)
    
    # Determine overall status
    all_passed = all(g.passed for g in guardrails)
    requires_approval = any(g.requires_human_approval for g in guardrails)
    
    if all_passed:
        status = ReadyToSendStatus.APPROVED
        can_send = True
    elif requires_approval:
        status = ReadyToSendStatus.SAFETY_HOLD
        can_send = False
    elif not contact_check.passed:
        status = ReadyToSendStatus.MISSING_CONTACT_INFO
        can_send = False
    elif not endorsement_check.passed:
        status = ReadyToSendStatus.INVALID_ENDORSEMENT_LIST
        can_send = False
    else:
        status = ReadyToSendStatus.PENDING_VALIDATION
        can_send = False
    
    return OutreachValidation(
        status=status,
        guardrails=guardrails,
        can_send=can_send,
        blocking_issues=blocking_issues
    )


def check_emergency_threshold(expiration_date: datetime) -> bool:
    """
    Check if license/insurance is in EMERGENCY_EXPIRING status (< 48hrs)
    For Presence-to-Paperwork trigger
    """
    hours_until = (expiration_date - datetime.now()).total_seconds() / 3600
    return 0 < hours_until < 48


def validate_presence_to_paperwork_trigger(
    contractor_uid: str,
    on_site: bool,
    expiration_status: str,
    expiration_date: Optional[datetime]
) -> Dict[str, Any]:
    """
    Validate conditions for emergency site alert
    
    Trigger: Contractor on-site + License/Insurance < 48hrs
    """
    should_trigger = False
    alert_level = "INFO"
    reason = ""
    
    if not on_site:
        reason = "Contractor not on-site"
    elif expiration_status == "VALID":
        reason = "Documentation valid"
    elif expiration_status == "EXPIRED":
        should_trigger = True
        alert_level = "CRITICAL"
        reason = "Contractor on-site with EXPIRED documentation"
    elif expiration_date and check_emergency_threshold(expiration_date):
        should_trigger = True
        alert_level = "EMERGENCY"
        reason = f"Contractor on-site with documentation expiring in < 48hrs"
    else:
        reason = "No emergency condition met"
    
    return {
        'should_trigger': should_trigger,
        'alert_level': alert_level,
        'reason': reason,
        'contractor_uid': contractor_uid,
        'timestamp': datetime.now().isoformat()
    }
