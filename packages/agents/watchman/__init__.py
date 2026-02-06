"""
Watchman (Sentinel-Scope) Agent - Site Reality Verification
Processes camera feeds to detect PPE compliance and cross-reference with Guard's database
"""
from .vision import WatchmanAgent, WatchmanOutput, SafetyAnalysis
from .logger import generate_daily_log, SiteAuditProof

__all__ = [
    "WatchmanAgent",
    "WatchmanOutput",
    "SafetyAnalysis",
    "generate_daily_log",
    "SiteAuditProof",
]
