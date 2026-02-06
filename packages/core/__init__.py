"""
Core Package - Unified Context for Multi-Agent System
Shared schemas to prevent data drift between DocumentAgent and WatchAgent

Following 'Governance-as-Code' principles for 2026 Construction Tech
"""
from .schemas import (
    # Document Models
    DocumentExtractionState,
    COIDocument,
    OSHALog,
    License,
    LienWaiver,
    ExtractedField,
    InsuranceCoverage,
    PIIRedaction,
    BrokerContact,
    
    # Decision Proof (XAI)
    DecisionProof,
    
    # Enums
    DocumentType,
    ExpirationStatus
)

from .governance import (
    ReadyToSendStatus,
    SafetyGuardrail,
    OutreachValidation,
    validate_ready_to_send,
    validate_presence_to_paperwork_trigger,
    check_emergency_threshold
)

__all__ = [
    # Document Models
    'DocumentExtractionState',
    'COIDocument',
    'OSHALog',
    'License',
    'LienWaiver',
    'ExtractedField',
    'InsuranceCoverage',
    'PIIRedaction',
    'BrokerContact',
    # Decision Proof
    'DecisionProof',
    # Enums
    'DocumentType',
    'ExpirationStatus',
    # Governance
    'ReadyToSendStatus',
    'SafetyGuardrail',
    'OutreachValidation',
    'validate_ready_to_send',
    'validate_presence_to_paperwork_trigger',
    'check_emergency_threshold'
]

__version__ = '2.0.0-autonomous'
