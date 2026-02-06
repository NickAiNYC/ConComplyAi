"""
Shared Pydantic Models Package
Used by both backend agents and frontend (via TypeScript generation)

9 Core Models:
1. DocumentExtractionState
2. COIDocument
3. OSHALog
4. License
5. LienWaiver
6. ExtractedField
7. InsuranceCoverage
8. PIIRedaction
9. AuditLogEntry (NEW for human-on-the-loop)
"""
from .document_models import (
    DocumentType,
    DocumentExtractionState,
    ExtractedField,
    SourceCoordinate,
    ExpirationStatus,
    PIIRedaction
)
from .insurance_models import (
    InsuranceCoverage,
    COIDocument
)
from .compliance_models import (
    OSHALog,
    License,
    LienWaiver
)
from .audit_models import (
    AuditLogEntry,
    AuditAction,
    DecisionLog
)

__all__ = [
    # Document models
    'DocumentType',
    'DocumentExtractionState',
    'ExtractedField',
    'SourceCoordinate',
    'ExpirationStatus',
    'PIIRedaction',
    # Insurance models
    'InsuranceCoverage',
    'COIDocument',
    # Compliance models
    'OSHALog',
    'License',
    'LienWaiver',
    # Audit models (NEW)
    'AuditLogEntry',
    'AuditAction',
    'DecisionLog'
]
