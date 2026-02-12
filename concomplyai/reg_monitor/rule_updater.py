"""Rule updater that assesses impact of regulatory changes and recommends actions.

Publishes ``regulation.updated`` events on the shared ``EventBus`` whenever
an impact assessment is created.
"""

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from concomplyai.core.event_bus import ComplianceEvent, EventBus
from concomplyai.reg_monitor.regulation_diff_engine import RegulationDiff

logger = logging.getLogger(__name__)


class ImpactAssessment(BaseModel):
    """Immutable record of a regulatory-change impact assessment."""

    model_config = ConfigDict(frozen=True)

    assessment_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for this assessment.",
    )
    diff_id: str = Field(
        ...,
        description="Identifier of the RegulationDiff that triggered this assessment.",
    )
    impacted_rules: list[str] = Field(
        default_factory=list,
        description="Rule identifiers affected by the regulatory change.",
    )
    risk_level: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] = Field(
        ...,
        description="Overall risk classification.",
    )
    requires_immediate_action: bool = Field(
        ...,
        description="Whether the change demands immediate human intervention.",
    )
    assessment_hash: str = Field(
        ...,
        description="SHA-256 integrity hash of the assessment payload.",
    )
    assessed_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when the assessment was produced.",
    )


class UpdateRecommendation(BaseModel):
    """Immutable recommendation for a single rule affected by a regulatory change."""

    model_config = ConfigDict(frozen=True)

    recommendation_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for this recommendation.",
    )
    rule_id: str = Field(
        ...,
        description="Identifier of the compliance rule this recommendation targets.",
    )
    action: Literal["UPDATE", "REVIEW", "DEPRECATE", "NO_ACTION"] = Field(
        ...,
        description="Recommended action to take on the rule.",
    )
    description: str = Field(
        ...,
        description="Human-readable explanation of the recommendation.",
    )
    priority: int = Field(
        ...,
        ge=1,
        le=5,
        description="Priority ranking from 1 (highest) to 5 (lowest).",
    )
    deadline_days: int = Field(
        ...,
        ge=0,
        description="Suggested number of days to complete the action.",
    )


class RuleUpdater:
    """Evaluates regulatory diffs, produces impact assessments, and generates recommendations.

    Publishes a ``regulation.updated`` event on the provided ``EventBus``
    each time an impact assessment is created.
    """

    def __init__(self, event_bus: EventBus) -> None:
        self._event_bus = event_bus

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_hash(data: dict) -> str:  # noqa: ANN401
        """Return the SHA-256 hex digest of *data* serialised as sorted JSON.

        Args:
            data: Dictionary payload to hash.

        Returns:
            Hex-encoded SHA-256 digest string.
        """
        serialised = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(serialised.encode("utf-8")).hexdigest()

    @staticmethod
    def _derive_risk_level(
        diff: RegulationDiff,
        affected_count: int,
    ) -> Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]:
        """Map diff severity and affected-rule count to a risk level.

        Args:
            diff: The regulation diff whose severity drives the base risk.
            affected_count: Number of compliance rules impacted.

        Returns:
            One of the four risk-level literals.
        """
        severity_rank = {
            "MINOR": 0,
            "MODERATE": 1,
            "MAJOR": 2,
            "BREAKING": 3,
        }
        base = severity_rank.get(diff.change_severity, 0)

        if affected_count > 10:
            base += 1
        if affected_count > 25:
            base += 1

        if base >= 3:
            return "CRITICAL"
        if base == 2:
            return "HIGH"
        if base == 1:
            return "MEDIUM"
        return "LOW"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def evaluate_impact(
        self,
        diff: RegulationDiff,
        affected_rules: list[str],
    ) -> ImpactAssessment:
        """Assess the impact of a regulatory diff on a set of compliance rules.

        A ``regulation.updated`` event is published to the event bus upon
        successful assessment creation.

        Args:
            diff: Structured diff of the regulation change.
            affected_rules: Identifiers of compliance rules that reference
                the changed regulation.

        Returns:
            An ``ImpactAssessment`` with risk level and integrity hash.
        """
        risk_level = self._derive_risk_level(diff, len(affected_rules))
        requires_action = risk_level in ("HIGH", "CRITICAL")

        hash_payload = {
            "diff_id": diff.diff_id,
            "impacted_rules": affected_rules,
            "risk_level": risk_level,
            "requires_immediate_action": requires_action,
        }
        assessment_hash = self._compute_hash(hash_payload)

        assessment = ImpactAssessment(
            diff_id=diff.diff_id,
            impacted_rules=affected_rules,
            risk_level=risk_level,
            requires_immediate_action=requires_action,
            assessment_hash=assessment_hash,
        )

        event = ComplianceEvent(
            event_type="regulation.updated",
            source="rule_updater",
            payload={
                "assessment_id": assessment.assessment_id,
                "diff_id": diff.diff_id,
                "risk_level": risk_level,
                "impacted_rule_count": len(affected_rules),
            },
            severity=risk_level if risk_level != "MEDIUM" else "MEDIUM",
        )
        self._event_bus.publish(event)

        logger.info(
            '{"action":"evaluate_impact","assessment_id":"%s","risk":"%s","rules":%d}',
            assessment.assessment_id,
            risk_level,
            len(affected_rules),
        )
        return assessment

    def generate_recommendations(
        self,
        assessment: ImpactAssessment,
    ) -> list[UpdateRecommendation]:
        """Produce actionable recommendations for each impacted rule.

        Recommendation priority and action are derived from the overall
        risk level of the assessment:

        * CRITICAL → UPDATE, priority 1, 7-day deadline
        * HIGH     → UPDATE, priority 2, 14-day deadline
        * MEDIUM   → REVIEW, priority 3, 30-day deadline
        * LOW      → NO_ACTION, priority 5, 90-day deadline

        Args:
            assessment: A previously computed ``ImpactAssessment``.

        Returns:
            List of ``UpdateRecommendation`` instances, one per impacted rule.
        """
        action_map: dict[str, tuple[Literal["UPDATE", "REVIEW", "DEPRECATE", "NO_ACTION"], int, int, str]] = {
            "CRITICAL": (
                "UPDATE",
                1,
                7,
                "Immediate rule update required due to critical regulatory change.",
            ),
            "HIGH": (
                "UPDATE",
                2,
                14,
                "Rule update recommended within two weeks due to high-impact change.",
            ),
            "MEDIUM": (
                "REVIEW",
                3,
                30,
                "Review rule for potential adjustments following moderate change.",
            ),
            "LOW": (
                "NO_ACTION",
                5,
                90,
                "No immediate action needed; schedule routine review.",
            ),
        }

        action, priority, deadline, description = action_map[assessment.risk_level]

        recommendations: list[UpdateRecommendation] = []
        for rule_id in assessment.impacted_rules:
            rec = UpdateRecommendation(
                rule_id=rule_id,
                action=action,
                description=description,
                priority=priority,
                deadline_days=deadline,
            )
            recommendations.append(rec)

        logger.info(
            '{"action":"generate_recommendations","assessment_id":"%s","count":%d}',
            assessment.assessment_id,
            len(recommendations),
        )
        return recommendations
