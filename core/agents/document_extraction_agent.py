"""Document Extraction Agent - OCR and field extraction for contractor documents"""
from typing import List, Dict, Any
from datetime import datetime
import hashlib
import re
from core.models import (
    DocumentExtractionState, ExtractedField, SourceCoordinate,
    PIIRedaction, AgentOutput, DocumentType
)
from core.config import calculate_token_cost


def extract_document_fields(state: DocumentExtractionState) -> dict:
    """
    Extract fields from contractor documents with confidence scoring and source coordinates
    
    RELIABILITY PRINCIPLE: Never hallucinate compliance data
    - All extractions include confidence scores
    - Source coordinates map to original document
    - PII is detected and can be redacted
    """
    try:
        # Simulate OCR extraction with realistic confidence scores
        # In production, this would call AWS Textract, GCP Vision, or Tesseract
        extracted_fields = []
        
        if state.document_type == DocumentType.COI:
            extracted_fields = _extract_coi_fields(state)
        elif state.document_type == DocumentType.LICENSE:
            extracted_fields = _extract_license_fields(state)
        elif state.document_type == DocumentType.OSHA_LOG:
            extracted_fields = _extract_osha_log_fields(state)
        elif state.document_type == DocumentType.LIEN_WAIVER:
            extracted_fields = _extract_lien_waiver_fields(state)
        else:
            raise ValueError(f"Unsupported document type: {state.document_type}")
        
        # Detect PII for redaction
        pii_redactions = _detect_pii(extracted_fields)
        
        # Calculate token cost (OCR + LLM parsing)
        input_tokens = 2000  # Document image tokens
        output_tokens = len(extracted_fields) * 50  # Field extraction
        cost = calculate_token_cost(input_tokens, output_tokens)
        
        print(f"[DOCUMENT_EXTRACTION] TOKEN_COST_USD: ${cost:.6f} (in={input_tokens}, out={output_tokens})")
        print(f"[DOCUMENT_EXTRACTION] Extracted {len(extracted_fields)} fields, found {len(pii_redactions)} PII items")
        
        # Create agent output
        agent_output = AgentOutput(
            agent_name="document_extraction_agent",
            status="success",
            tokens_used=input_tokens + output_tokens,
            usd_cost=cost,
            timestamp=datetime.now(),
            data={
                "fields_extracted": len(extracted_fields),
                "pii_detected": len(pii_redactions),
                "document_type": state.document_type.value,
                "avg_confidence": sum(f.confidence for f in extracted_fields) / len(extracted_fields) if extracted_fields else 0.0
            }
        )
        
        agent_outputs = state.agent_outputs.copy()
        agent_outputs.append(agent_output)
        
        return {
            "extracted_fields": extracted_fields,
            "pii_redactions": pii_redactions,
            "agent_outputs": agent_outputs,
            "total_tokens": state.total_tokens + input_tokens + output_tokens,
            "total_cost": state.total_cost + cost
        }
        
    except Exception as e:
        # ROBUST ERROR HANDLING: Never let OCR failures crash the system
        print(f"[DOCUMENT_EXTRACTION] ERROR: {str(e)}")
        agent_output = AgentOutput(
            agent_name="document_extraction_agent",
            status="error",
            tokens_used=0,
            usd_cost=0.0,
            timestamp=datetime.now(),
            data={"error": str(e)}
        )
        
        agent_outputs = state.agent_outputs.copy()
        agent_outputs.append(agent_output)
        
        return {
            "validation_errors": state.validation_errors + [f"Extraction failed: {str(e)}"],
            "agent_outputs": agent_outputs
        }


def _extract_coi_fields(state: DocumentExtractionState) -> List[ExtractedField]:
    """
    Extract Certificate of Insurance fields with source coordinates
    
    DOMAIN KNOWLEDGE: COI must include:
    - Additional Insured endorsement
    - Waiver of Subrogation
    - Per Project Aggregate (for GL coverage)
    """
    fields = [
        ExtractedField(
            field_name="contractor_name",
            value="ABC Construction LLC",
            confidence=0.95,
            source_coordinate=SourceCoordinate(page=1, x=0.1, y=0.15, width=0.3, height=0.02),
            extraction_method="OCR"
        ),
        ExtractedField(
            field_name="policy_number",
            value="GL-2024-789456",
            confidence=0.92,
            source_coordinate=SourceCoordinate(page=1, x=0.5, y=0.3, width=0.25, height=0.02),
            extraction_method="OCR"
        ),
        ExtractedField(
            field_name="effective_date",
            value="2024-01-01",
            confidence=0.89,
            source_coordinate=SourceCoordinate(page=1, x=0.1, y=0.35, width=0.15, height=0.02),
            extraction_method="OCR"
        ),
        ExtractedField(
            field_name="expiration_date",
            value="2025-01-01",
            confidence=0.91,
            source_coordinate=SourceCoordinate(page=1, x=0.3, y=0.35, width=0.15, height=0.02),
            extraction_method="OCR"
        ),
        ExtractedField(
            field_name="general_liability_limit",
            value="2000000",  # $2M per occurrence
            confidence=0.88,
            source_coordinate=SourceCoordinate(page=1, x=0.6, y=0.4, width=0.15, height=0.02),
            extraction_method="OCR"
        ),
        ExtractedField(
            field_name="aggregate_limit",
            value="4000000",  # $4M aggregate
            confidence=0.87,
            source_coordinate=SourceCoordinate(page=1, x=0.6, y=0.42, width=0.15, height=0.02),
            extraction_method="OCR"
        ),
        ExtractedField(
            field_name="additional_insured",
            value="YES",
            confidence=0.94,
            source_coordinate=SourceCoordinate(page=1, x=0.1, y=0.6, width=0.1, height=0.02),
            extraction_method="LLM"  # Checkbox detection
        ),
        ExtractedField(
            field_name="waiver_of_subrogation",
            value="YES",
            confidence=0.93,
            source_coordinate=SourceCoordinate(page=1, x=0.1, y=0.62, width=0.1, height=0.02),
            extraction_method="LLM"
        ),
        ExtractedField(
            field_name="per_project_aggregate",
            value="YES",
            confidence=0.90,
            source_coordinate=SourceCoordinate(page=1, x=0.1, y=0.64, width=0.1, height=0.02),
            extraction_method="LLM"
        ),
        ExtractedField(
            field_name="certificate_holder",
            value="Project Owner ABC",
            confidence=0.96,
            source_coordinate=SourceCoordinate(page=1, x=0.1, y=0.8, width=0.4, height=0.05),
            extraction_method="OCR"
        )
    ]
    
    return fields


def _extract_license_fields(state: DocumentExtractionState) -> List[ExtractedField]:
    """Extract contractor license fields"""
    fields = [
        ExtractedField(
            field_name="license_number",
            value="CTR-2024-12345",
            confidence=0.94,
            source_coordinate=SourceCoordinate(page=1, x=0.2, y=0.2, width=0.2, height=0.02),
            extraction_method="OCR"
        ),
        ExtractedField(
            field_name="license_type",
            value="General Contractor - Class A",
            confidence=0.91,
            source_coordinate=SourceCoordinate(page=1, x=0.2, y=0.25, width=0.3, height=0.02),
            extraction_method="OCR"
        ),
        ExtractedField(
            field_name="licensee_name",
            value="John Smith",
            confidence=0.93,
            source_coordinate=SourceCoordinate(page=1, x=0.2, y=0.3, width=0.25, height=0.02),
            extraction_method="OCR"
        ),
        ExtractedField(
            field_name="issue_date",
            value="2024-01-15",
            confidence=0.88,
            source_coordinate=SourceCoordinate(page=1, x=0.2, y=0.4, width=0.15, height=0.02),
            extraction_method="OCR"
        ),
        ExtractedField(
            field_name="expiration_date",
            value="2026-01-15",
            confidence=0.89,
            source_coordinate=SourceCoordinate(page=1, x=0.4, y=0.4, width=0.15, height=0.02),
            extraction_method="OCR"
        )
    ]
    
    return fields


def _extract_osha_log_fields(state: DocumentExtractionState) -> List[ExtractedField]:
    """Extract OSHA 300/300A log fields"""
    fields = [
        ExtractedField(
            field_name="establishment_name",
            value="ABC Construction LLC",
            confidence=0.95,
            source_coordinate=SourceCoordinate(page=1, x=0.1, y=0.1, width=0.3, height=0.02),
            extraction_method="OCR"
        ),
        ExtractedField(
            field_name="year",
            value="2024",
            confidence=0.99,
            source_coordinate=SourceCoordinate(page=1, x=0.5, y=0.1, width=0.1, height=0.02),
            extraction_method="OCR"
        ),
        ExtractedField(
            field_name="total_recordable_cases",
            value="3",
            confidence=0.92,
            source_coordinate=SourceCoordinate(page=1, x=0.3, y=0.5, width=0.05, height=0.02),
            extraction_method="OCR"
        ),
        ExtractedField(
            field_name="days_away_from_work",
            value="15",
            confidence=0.90,
            source_coordinate=SourceCoordinate(page=1, x=0.4, y=0.5, width=0.05, height=0.02),
            extraction_method="OCR"
        )
    ]
    
    return fields


def _extract_lien_waiver_fields(state: DocumentExtractionState) -> List[ExtractedField]:
    """Extract lien waiver fields"""
    fields = [
        ExtractedField(
            field_name="waiver_type",
            value="Conditional Partial",
            confidence=0.91,
            source_coordinate=SourceCoordinate(page=1, x=0.1, y=0.15, width=0.2, height=0.02),
            extraction_method="LLM"
        ),
        ExtractedField(
            field_name="contractor_name",
            value="ABC Construction LLC",
            confidence=0.94,
            source_coordinate=SourceCoordinate(page=1, x=0.1, y=0.25, width=0.3, height=0.02),
            extraction_method="OCR"
        ),
        ExtractedField(
            field_name="project_name",
            value="Hudson Yards Tower B",
            confidence=0.92,
            source_coordinate=SourceCoordinate(page=1, x=0.1, y=0.3, width=0.3, height=0.02),
            extraction_method="OCR"
        ),
        ExtractedField(
            field_name="through_date",
            value="2024-12-31",
            confidence=0.88,
            source_coordinate=SourceCoordinate(page=1, x=0.1, y=0.4, width=0.15, height=0.02),
            extraction_method="OCR"
        ),
        ExtractedField(
            field_name="amount",
            value="$125,000.00",
            confidence=0.90,
            source_coordinate=SourceCoordinate(page=1, x=0.3, y=0.4, width=0.15, height=0.02),
            extraction_method="OCR"
        ),
        ExtractedField(
            field_name="signature_present",
            value="true",
            confidence=0.85,
            source_coordinate=SourceCoordinate(page=1, x=0.1, y=0.8, width=0.2, height=0.05),
            extraction_method="LLM"
        )
    ]
    
    return fields


def _detect_pii(fields: List[ExtractedField]) -> List[PIIRedaction]:
    """
    PRIVACY BY DESIGN: Detect PII before sending to third-party APIs
    
    Patterns:
    - SSN: XXX-XX-XXXX
    - Phone: (XXX) XXX-XXXX
    - Email: ***@***.com
    """
    pii_redactions = []
    
    # SSN pattern
    ssn_pattern = re.compile(r'\b\d{3}-\d{2}-\d{4}\b')
    # Phone pattern
    phone_pattern = re.compile(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b')
    # Email pattern
    email_pattern = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
    
    for field in fields:
        value_str = str(field.value)
        
        # Check for SSN
        if ssn_pattern.search(value_str):
            original_hash = hashlib.sha256(value_str.encode()).hexdigest()
            redacted = re.sub(r'\d{3}-\d{2}-(\d{4})', r'***-**-\1', value_str)
            pii_redactions.append(PIIRedaction(
                field_name=field.field_name,
                original_value_hash=original_hash,
                pii_type="SSN",
                redacted_value=redacted,
                redaction_method="regex"
            ))
            field.redacted = True
        
        # Check for phone
        if phone_pattern.search(value_str):
            original_hash = hashlib.sha256(value_str.encode()).hexdigest()
            redacted = re.sub(r'\d{3}[-.]?\d{3}[-.]?(\d{4})', r'***-***-\1', value_str)
            pii_redactions.append(PIIRedaction(
                field_name=field.field_name,
                original_value_hash=original_hash,
                pii_type="Phone",
                redacted_value=redacted,
                redaction_method="regex"
            ))
            field.redacted = True
        
        # Check for email
        if email_pattern.search(value_str):
            original_hash = hashlib.sha256(value_str.encode()).hexdigest()
            # More secure redaction - mask entire email
            redacted = '***@***'
            pii_redactions.append(PIIRedaction(
                field_name=field.field_name,
                original_value_hash=original_hash,
                pii_type="Email",
                redacted_value=redacted,
                redaction_method="regex"
            ))
            field.redacted = True
    
    return pii_redactions
