"""
Monitoring Package - Agent Governance & Quality Dashboard
Implements enterprise telemetry and compliance tracking for 2026-2027 standards.
"""
from .telemetry_service import (
    TelemetryService,
    AgentFlowMetric,
    HumanOverrideEvent,
    TokenCostAttribution,
    TTFTMetric,
    AgentType,
    FlowOutcome,
    OverrideReason,
    get_telemetry_service
)
from .bias_auditor import (
    BiasAuditor,
    BiasAuditLog,
    AdversarialTestResult,
    BiasCategory,
    get_bias_auditor
)
from .governance_proof import (
    GovernanceProof,
    LegalSandboxStatus,
    StrictLiabilityTrigger,
    TriggerMatch,
    LegalSandbox,
    get_legal_sandbox
)
from .immutable_logger import (
    ImmutableLogger,
    ImmutableLogEntry,
    get_immutable_logger
)

__all__ = [
    # Telemetry
    'TelemetryService',
    'AgentFlowMetric',
    'HumanOverrideEvent',
    'TokenCostAttribution',
    'TTFTMetric',
    'AgentType',
    'FlowOutcome',
    'OverrideReason',
    'get_telemetry_service',
    # Bias Auditing
    'BiasAuditor',
    'BiasAuditLog',
    'AdversarialTestResult',
    'BiasCategory',
    'get_bias_auditor',
    # Governance
    'GovernanceProof',
    'LegalSandboxStatus',
    'StrictLiabilityTrigger',
    'TriggerMatch',
    'LegalSandbox',
    'get_legal_sandbox',
    # Immutable Logging
    'ImmutableLogger',
    'ImmutableLogEntry',
    'get_immutable_logger'
]

__version__ = '1.0.0-governance'
