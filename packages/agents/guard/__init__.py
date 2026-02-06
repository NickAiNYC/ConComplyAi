"""Guard Agent - Certificate of Insurance Validation Package"""

from .validator import validate_coi as validate_coi_legacy, ComplianceResult
from .core import validate_coi, GuardOutput

__all__ = ["validate_coi", "validate_coi_legacy", "ComplianceResult", "GuardOutput"]
