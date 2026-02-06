"""Insurance Validation Agent - Domain-specific COI compliance checking"""
from typing import List, Dict, Any
from datetime import datetime, timedelta
from core.models import (
    DocumentExtractionState, ExtractedField, AgentOutput,
    ExpirationStatus, DocumentType
)
from core.config import calculate_token_cost


def validate_insurance_requirements(state: DocumentExtractionState) -> dict:
    """
    DOMAIN KNOWLEDGE: Insurance Logic
    - Additional Insured: Certificate holder must be added to contractor's GL policy
    - Waiver of Subrogation: Insurer waives right to sue certificate holder
    - Per Project Aggregate: Separate $4M aggregate for this project only
    - Minimum Limits: $2M per occurrence, $4M aggregate for GL
    
    COMPLIANCE CANNOT HAVE HALLUCINATIONS: All validations are deterministic
    """
    if state.document_type != DocumentType.COI:
        return {"validation_errors": state.validation_errors + ["Not a COI document"]}
    
    try:
        # Extract insurance-specific fields
        fields_dict = {field.field_name: field for field in state.extracted_fields}
        
        validation_errors = []
        validation_passed = True
        
        # 1. CHECK ADDITIONAL INSURED
        has_additional_insured = _check_field_value(
            fields_dict.get("additional_insured"),
            expected_values=["YES", "True", "X"],
            error_msg="Additional Insured endorsement missing or not checked"
        )
        if not has_additional_insured:
            validation_errors.append("CRITICAL: Additional Insured endorsement not found")
            validation_passed = False
        
        # 2. CHECK WAIVER OF SUBROGATION
        has_waiver = _check_field_value(
            fields_dict.get("waiver_of_subrogation"),
            expected_values=["YES", "True", "X"],
            error_msg="Waiver of Subrogation not found"
        )
        if not has_waiver:
            validation_errors.append("CRITICAL: Waiver of Subrogation not found")
            validation_passed = False
        
        # 3. CHECK PER PROJECT AGGREGATE
        has_per_project = _check_field_value(
            fields_dict.get("per_project_aggregate"),
            expected_values=["YES", "True", "X"],
            error_msg="Per Project Aggregate not specified"
        )
        if not has_per_project:
            validation_errors.append("WARNING: Per Project Aggregate not specified (recommended for large projects)")
        
        # 4. VALIDATE COVERAGE LIMITS
        gl_limit = _parse_currency(fields_dict.get("general_liability_limit"))
        aggregate_limit = _parse_currency(fields_dict.get("aggregate_limit"))
        
        if gl_limit and gl_limit < 2000000:
            validation_errors.append(f"CRITICAL: GL per occurrence limit ${gl_limit:,} below minimum $2,000,000")
            validation_passed = False
        
        if aggregate_limit and aggregate_limit < 4000000:
            validation_errors.append(f"CRITICAL: Aggregate limit ${aggregate_limit:,} below minimum $4,000,000")
            validation_passed = False
        
        # 5. CHECK EXPIRATION STATUS
        expiration_status = _check_expiration_date(fields_dict.get("expiration_date"))
        
        if expiration_status == ExpirationStatus.EXPIRED:
            validation_errors.append("CRITICAL: Insurance policy has EXPIRED")
            validation_passed = False
        elif expiration_status == ExpirationStatus.EXPIRING_SOON:
            validation_errors.append("WARNING: Insurance policy expiring within 30 days")
        
        # 6. VALIDATE CERTIFICATE HOLDER
        cert_holder = fields_dict.get("certificate_holder")
        if not cert_holder or not cert_holder.value or cert_holder.confidence < 0.8:
            validation_errors.append("WARNING: Certificate holder name unclear or missing")
        
        # Calculate cost
        input_tokens = len(state.extracted_fields) * 20  # Read extracted fields
        output_tokens = 300  # Validation logic
        cost = calculate_token_cost(input_tokens, output_tokens)
        
        print(f"[INSURANCE_VALIDATION] TOKEN_COST_USD: ${cost:.6f} (in={input_tokens}, out={output_tokens})")
        print(f"[INSURANCE_VALIDATION] Passed: {validation_passed}, Errors: {len(validation_errors)}")
        print(f"[INSURANCE_VALIDATION] Additional Insured: {has_additional_insured}, Waiver: {has_waiver}, Per Project: {has_per_project}")
        
        agent_output = AgentOutput(
            agent_name="insurance_validation_agent",
            status="success",
            tokens_used=input_tokens + output_tokens,
            usd_cost=cost,
            timestamp=datetime.now(),
            data={
                "validation_passed": validation_passed,
                "errors_count": len(validation_errors),
                "has_additional_insured": has_additional_insured,
                "has_waiver_of_subrogation": has_waiver,
                "has_per_project_aggregate": has_per_project,
                "expiration_status": expiration_status.value,
                "gl_limit": gl_limit,
                "aggregate_limit": aggregate_limit
            }
        )
        
        agent_outputs = state.agent_outputs.copy()
        agent_outputs.append(agent_output)
        
        return {
            "validation_passed": validation_passed,
            "validation_errors": state.validation_errors + validation_errors,
            "agent_outputs": agent_outputs,
            "total_tokens": state.total_tokens + input_tokens + output_tokens,
            "total_cost": state.total_cost + cost
        }
        
    except Exception as e:
        print(f"[INSURANCE_VALIDATION] ERROR: {str(e)}")
        agent_output = AgentOutput(
            agent_name="insurance_validation_agent",
            status="error",
            tokens_used=0,
            usd_cost=0.0,
            timestamp=datetime.now(),
            data={"error": str(e)}
        )
        
        agent_outputs = state.agent_outputs.copy()
        agent_outputs.append(agent_output)
        
        return {
            "validation_passed": False,
            "validation_errors": state.validation_errors + [f"Validation failed: {str(e)}"],
            "agent_outputs": agent_outputs
        }


def _check_field_value(field: ExtractedField, expected_values: List[str], error_msg: str) -> bool:
    """
    Check if extracted field matches expected values
    Returns True if field exists and matches
    """
    if not field:
        return False
    
    value_str = str(field.value).strip().upper()
    return any(value_str == expected.upper() for expected in expected_values)


def _parse_currency(field: ExtractedField) -> float:
    """Parse currency value from field"""
    if not field or not field.value:
        return 0.0
    
    # Remove currency symbols and commas
    value_str = str(field.value).replace('$', '').replace(',', '').strip()
    
    try:
        return float(value_str)
    except (ValueError, TypeError):
        return 0.0


def _check_expiration_date(field: ExtractedField) -> ExpirationStatus:
    """
    VERIFICATION LOGIC: Compare expiration date against current date
    - Expired: Date in the past
    - Expiring Soon: Within 30 days
    - Valid: More than 30 days remaining
    """
    if not field or not field.value:
        return ExpirationStatus.NO_EXPIRATION
    
    try:
        # Parse date (supports YYYY-MM-DD, MM/DD/YYYY formats)
        date_str = str(field.value)
        
        if '-' in date_str:
            # ISO format: YYYY-MM-DD
            expiration_date = datetime.strptime(date_str, "%Y-%m-%d")
        elif '/' in date_str:
            # US format: MM/DD/YYYY
            expiration_date = datetime.strptime(date_str, "%m/%d/%Y")
        else:
            return ExpirationStatus.NO_EXPIRATION
        
        today = datetime.now()
        days_until_expiration = (expiration_date - today).days
        
        if days_until_expiration < 0:
            return ExpirationStatus.EXPIRED
        elif days_until_expiration <= 30:
            return ExpirationStatus.EXPIRING_SOON
        else:
            return ExpirationStatus.VALID
            
    except (ValueError, TypeError):
        return ExpirationStatus.NO_EXPIRATION


def validate_license_expiration(state: DocumentExtractionState) -> dict:
    """Validate contractor license expiration"""
    if state.document_type != DocumentType.LICENSE:
        return {"validation_errors": state.validation_errors + ["Not a license document"]}
    
    try:
        fields_dict = {field.field_name: field for field in state.extracted_fields}
        validation_errors = []
        validation_passed = True
        
        # Check expiration
        expiration_status = _check_expiration_date(fields_dict.get("expiration_date"))
        
        if expiration_status == ExpirationStatus.EXPIRED:
            validation_errors.append("CRITICAL: Contractor license has EXPIRED")
            validation_passed = False
        elif expiration_status == ExpirationStatus.EXPIRING_SOON:
            validation_errors.append("WARNING: Contractor license expiring within 30 days")
        
        # Verify license number format
        license_num = fields_dict.get("license_number")
        if not license_num or not license_num.value:
            validation_errors.append("CRITICAL: License number missing")
            validation_passed = False
        elif license_num.confidence < 0.85:
            validation_errors.append("WARNING: License number confidence low - manual verification recommended")
        
        # Calculate cost
        input_tokens = len(state.extracted_fields) * 15
        output_tokens = 200
        cost = calculate_token_cost(input_tokens, output_tokens)
        
        print(f"[LICENSE_VALIDATION] TOKEN_COST_USD: ${cost:.6f} (in={input_tokens}, out={output_tokens})")
        print(f"[LICENSE_VALIDATION] Expiration Status: {expiration_status.value}")
        
        agent_output = AgentOutput(
            agent_name="license_validation_agent",
            status="success",
            tokens_used=input_tokens + output_tokens,
            usd_cost=cost,
            timestamp=datetime.now(),
            data={
                "validation_passed": validation_passed,
                "expiration_status": expiration_status.value,
                "errors_count": len(validation_errors)
            }
        )
        
        agent_outputs = state.agent_outputs.copy()
        agent_outputs.append(agent_output)
        
        return {
            "validation_passed": validation_passed,
            "validation_errors": state.validation_errors + validation_errors,
            "agent_outputs": agent_outputs,
            "total_tokens": state.total_tokens + input_tokens + output_tokens,
            "total_cost": state.total_cost + cost
        }
        
    except Exception as e:
        print(f"[LICENSE_VALIDATION] ERROR: {str(e)}")
        return {
            "validation_passed": False,
            "validation_errors": state.validation_errors + [f"License validation failed: {str(e)}"]
        }
