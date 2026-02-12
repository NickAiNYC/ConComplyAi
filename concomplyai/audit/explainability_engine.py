"""Explainability Engine — human-readable explanations for compliance decisions.

Translates raw ``DecisionLogEntry`` records and numeric risk scores into
plain-language summaries suitable for regulators, legal teams, and
non-technical stakeholders.  Satisfies NYC Local Law 144 and EU AI Act
Article 13 transparency requirements.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field

from concomplyai.audit.decision_logger import DecisionLogEntry

_CONFIDENCE_THRESHOLDS = {
    "HIGH CONFIDENCE": 0.8,
    "MODERATE CONFIDENCE": 0.5,
}


def _assess_confidence(confidence: float) -> str:
    """Map a numeric confidence value to a human-readable label."""
    if confidence >= _CONFIDENCE_THRESHOLDS["HIGH CONFIDENCE"]:
        return "HIGH CONFIDENCE"
    if confidence >= _CONFIDENCE_THRESHOLDS["MODERATE CONFIDENCE"]:
        return "MODERATE CONFIDENCE"
    return "LOW CONFIDENCE"


class DecisionExplanation(BaseModel):
    """Immutable, human-readable explanation of a compliance decision."""

    model_config = ConfigDict(frozen=True)

    explanation_id: str = Field(description="Unique identifier (UUID) for this explanation.")
    decision_id: str = Field(description="ID of the decision being explained.")
    agent_name: str = Field(description="Agent that produced the original decision.")
    plain_language_summary: str = Field(description="Non-technical summary of the decision.")
    key_factors: list[str] = Field(description="Primary factors that drove the decision.")
    confidence_assessment: str = Field(
        description="Human-readable confidence label: HIGH / MODERATE / LOW CONFIDENCE."
    )
    regulatory_references: list[str] = Field(
        default_factory=list,
        description="Applicable regulatory citations.",
    )
    generated_at: datetime = Field(description="UTC timestamp of explanation generation.")


class ExplainabilityEngine:
    """Generates plain-language explanations for compliance decisions and risk scores."""

    def explain_decision(self, entry: DecisionLogEntry) -> DecisionExplanation:
        """Produce a ``DecisionExplanation`` from a logged decision.

        Args:
            entry: The ``DecisionLogEntry`` to explain.

        Returns:
            A frozen ``DecisionExplanation`` model.
        """
        confidence_label = _assess_confidence(entry.confidence)

        key_factors: list[str] = [
            f"Agent '{entry.agent_name}' evaluated the input and reached a '{entry.decision}' outcome.",
            f"Confidence level: {entry.confidence:.0%} ({confidence_label}).",
        ]
        if entry.reasoning:
            key_factors.append(f"Reasoning: {entry.reasoning}")

        summary = (
            f"The {entry.agent_name} agent determined '{entry.decision}' "
            f"with {entry.confidence:.0%} confidence. "
            f"{entry.reasoning}"
        )

        regulatory_refs: list[str] = entry.metadata.get("regulatory_references", [])

        return DecisionExplanation(
            explanation_id=str(uuid.uuid4()),
            decision_id=entry.decision_id,
            agent_name=entry.agent_name,
            plain_language_summary=summary,
            key_factors=key_factors,
            confidence_assessment=confidence_label,
            regulatory_references=regulatory_refs,
            generated_at=datetime.now(timezone.utc),
        )

    def explain_risk_score(self, score: float, factors: list[dict[str, str]]) -> str:
        """Explain how a numeric risk score was derived from contributing factors.

        Args:
            score: Overall risk score (0–100 scale).
            factors: List of dicts, each with ``"name"`` and ``"impact"`` keys
                     describing a contributing factor.

        Returns:
            A multi-line human-readable explanation string.
        """
        lines: list[str] = [
            f"Risk Score: {score:.1f}/100",
            "",
            "Contributing Factors:",
        ]
        if not factors:
            lines.append("  No contributing factors were recorded.")
        else:
            for factor in factors:
                name = factor.get("name", "Unknown factor")
                impact = factor.get("impact", "unspecified impact")
                lines.append(f"  - {name}: {impact}")

        lines.append("")

        if score >= 75:
            lines.append("Assessment: HIGH RISK — immediate attention required.")
        elif score >= 40:
            lines.append("Assessment: MODERATE RISK — review recommended.")
        else:
            lines.append("Assessment: LOW RISK — within acceptable thresholds.")

        return "\n".join(lines)
