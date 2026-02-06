"""
Guard Agent Core - Enhanced with AgentHandshakeV2 Support
Refactored to inherit from AgentOutputProtocol for multi-agent consistency

This module wraps the existing validator.py functionality with the new protocol.
"""
from typing import Optional, Dict, Any
from pathlib import Path
from datetime import datetime

from packages.core.agent_protocol import (
    AgentRole, AgentHandshakeV2, AgentOutputProtocol,
    create_guard_handshake
)
from packages.core.audit import DecisionProof

from .validator import validate_coi as _validate_coi_internal, ComplianceResult


class GuardOutput(AgentOutputProtocol):
    """
    Guard Agent output conforming to AgentOutputProtocol
    Wraps the existing ComplianceResult with handshake integration
    """
    compliance_result: ComplianceResult
    
    class Config:
        frozen = True


def validate_coi(
    pdf_path: Path,
    parent_handshake: Optional[AgentHandshakeV2] = None,
    project_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Validate Certificate of Insurance with AgentHandshakeV2 support
    
    This is the new entry point for Guard validation that supports
    the multi-agent handshake protocol.
    
    Args:
        pdf_path: Path to COI PDF file
        parent_handshake: Optional handshake from Scout agent (or other parent)
        project_id: Optional project ID (derived from parent_handshake if provided)
    
    Returns:
        Dict containing:
        - compliance_result: ComplianceResult from validation
        - handshake: AgentHandshakeV2 for next agent in chain
        - guard_output: GuardOutput conforming to AgentOutputProtocol
        - decision_proof_obj: DecisionProof object
        - cost_usd: Processing cost
        - input_tokens: Token usage
        - output_tokens: Token usage
    """
    # Call the internal validation function
    internal_result = _validate_coi_internal(pdf_path)
    
    # Extract results
    compliance_result: ComplianceResult = internal_result["result"]
    decision_proof_obj: DecisionProof = internal_result["decision_proof_obj"]
    cost_usd: float = internal_result["cost_usd"]
    
    # Determine project_id
    if project_id is None:
        if parent_handshake:
            project_id = parent_handshake.project_id
        else:
            # Generate project ID from document
            project_id = f"GUARD-{compliance_result.document_id}"
    
    # Create Guard handshake for next agent
    handshake = create_guard_handshake(
        decision_proof_hash=decision_proof_obj.proof_hash,
        project_id=project_id,
        status=compliance_result.status,
        parent_handshake=parent_handshake
    )
    
    # Create GuardOutput conforming to AgentOutputProtocol
    guard_output = GuardOutput(
        handshake=handshake,
        decision_proof_hash=decision_proof_obj.proof_hash,
        processing_cost_usd=cost_usd,
        confidence_score=compliance_result.confidence_score,
        agent_name=AgentRole.GUARD,
        compliance_result=compliance_result
    )
    
    # Return enhanced result with handshake
    return {
        **internal_result,  # Include all original fields
        "compliance_result": compliance_result,
        "handshake": handshake,
        "guard_output": guard_output,
        "project_id": project_id,
    }
