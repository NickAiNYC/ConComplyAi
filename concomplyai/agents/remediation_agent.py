"""Autonomous remediation agent for compliance violations.

Subscribes to ``compliance.violation`` events on the shared
:class:`~concomplyai.core.event_bus.EventBus` and produces a
:class:`RemediationAction` with a SHA-256 decision proof for every
incoming violation.
"""

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from concomplyai.core.event_bus import ComplianceEvent, EventBus

logger = logging.getLogger(__name__)

_SEVERITY_TO_ACTION: dict[str, Literal["AUTO_FIX", "MANUAL_REVIEW", "ESCALATE", "NOTIFY"]] = {
    "CRITICAL": "ESCALATE",
    "HIGH": "MANUAL_REVIEW",
    "MEDIUM": "AUTO_FIX",
    "LOW": "NOTIFY",
}

_SEVERITY_TO_PRIORITY: dict[str, int] = {
    "CRITICAL": 1,
    "HIGH": 2,
    "MEDIUM": 3,
    "LOW": 4,
}


class RemediationAction(BaseModel):
    """Immutable record of a remediation decision with cryptographic proof."""

    model_config = ConfigDict(frozen=True)

    action_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for this remediation action.",
    )
    violation_id: str = Field(
        ...,
        description="Identifier of the violation being remediated.",
    )
    action_type: Literal["AUTO_FIX", "MANUAL_REVIEW", "ESCALATE", "NOTIFY"] = Field(
        ...,
        description="Category of remediation to apply.",
    )
    description: str = Field(
        ...,
        description="Human-readable description of the remediation action.",
    )
    priority: int = Field(
        ...,
        ge=1,
        le=5,
        description="Priority level from 1 (highest) to 5 (lowest).",
    )
    assigned_to: Optional[str] = Field(
        default=None,
        description="User or team assigned to carry out the action.",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of action creation.",
    )
    reasoning: str = Field(
        ...,
        description="Explanation of why this action type was chosen.",
    )
    decision_hash: str = Field(
        ...,
        description="SHA-256 hash of the decision inputs for audit proof.",
    )


def _compute_decision_hash(
    violation_id: str,
    severity: str,
    action_type: str,
    reasoning: str,
) -> str:
    """Return a SHA-256 hex digest over the key decision inputs."""
    content = json.dumps(
        {
            "violation_id": violation_id,
            "severity": severity,
            "action_type": action_type,
            "reasoning": reasoning,
        },
        sort_keys=True,
    )
    return hashlib.sha256(content.encode()).hexdigest()


class RemediationAgent:
    """Decides and records remediation actions for compliance violations.

    On instantiation the agent subscribes to ``compliance.violation`` events
    on the provided :class:`EventBus`.  Each violation is mapped to an
    appropriate :class:`RemediationAction` based on severity, and the
    decision is logged with a SHA-256 proof hash.
    """

    def __init__(self, event_bus: EventBus) -> None:
        self._event_bus = event_bus
        self._actions: list[RemediationAction] = []
        self._event_bus.subscribe("compliance.violation", self.handle_violation)
        logger.info('{"agent":"RemediationAgent","action":"initialized"}')

    def handle_violation(self, event: ComplianceEvent) -> RemediationAction:
        """Determine the appropriate remediation for *event*.

        Args:
            event: A ``compliance.violation`` event carrying violation
                details in its payload.

        Returns:
            A frozen :class:`RemediationAction` with SHA-256 decision proof.
        """
        severity = event.severity
        violation_id = event.payload.get("violation_id", event.event_id)
        action_type = _SEVERITY_TO_ACTION.get(severity, "MANUAL_REVIEW")
        priority = _SEVERITY_TO_PRIORITY.get(severity, 3)

        reasoning = (
            f"Violation {violation_id} classified as {severity}. "
            f"Policy maps {severity} severity to {action_type} action type "
            f"with priority {priority}."
        )

        if severity == "CRITICAL":
            assigned_to = "compliance-lead"
            description = (
                f"ESCALATE: Critical violation {violation_id} requires "
                "immediate senior review and regulatory notification."
            )
        elif severity == "HIGH":
            assigned_to = "compliance-team"
            description = (
                f"MANUAL_REVIEW: High-severity violation {violation_id} "
                "requires expert assessment before remediation."
            )
        elif severity == "MEDIUM":
            assigned_to = None
            description = (
                f"AUTO_FIX: Medium-severity violation {violation_id} "
                "can be resolved automatically per remediation playbook."
            )
        else:
            assigned_to = None
            description = (
                f"NOTIFY: Low-severity violation {violation_id} logged "
                "and stakeholders notified for awareness."
            )

        decision_hash = _compute_decision_hash(
            violation_id, severity, action_type, reasoning,
        )

        action = RemediationAction(
            violation_id=violation_id,
            action_type=action_type,
            description=description,
            priority=priority,
            assigned_to=assigned_to,
            reasoning=reasoning,
            decision_hash=decision_hash,
        )

        self._actions.append(action)

        logger.info(
            '{"agent":"RemediationAgent","action":"remediation_decided",'
            '"violation_id":"%s","action_type":"%s","priority":%d,'
            '"decision_hash":"%s"}',
            violation_id,
            action_type,
            priority,
            decision_hash,
        )

        return action
