"""
Fixer Agent - Autonomous Remediation Outreach
Part of the Scout → Guard → Fixer Triple Handshake
"""

from .outreach import OutreachAgent, FixerOutput, draft_broker_email

__all__ = ["OutreachAgent", "FixerOutput", "draft_broker_email"]
