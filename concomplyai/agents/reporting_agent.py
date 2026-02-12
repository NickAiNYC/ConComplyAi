"""Compliance reporting agent for generating audit-ready reports.

Subscribes to ``compliance.report_request`` events and produces a
:class:`ComplianceReport` with weighted compliance scoring and a
SHA-256 integrity hash.
"""

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from concomplyai.core.event_bus import ComplianceEvent, EventBus

logger = logging.getLogger(__name__)

_SEVERITY_WEIGHTS: dict[str, float] = {
    "CRITICAL": 10.0,
    "HIGH": 5.0,
    "MEDIUM": 2.0,
    "LOW": 0.5,
}


class ComplianceReport(BaseModel):
    """Immutable compliance report with cryptographic integrity proof."""

    model_config = ConfigDict(frozen=True)

    report_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for this report.",
    )
    title: str = Field(
        ...,
        description="Report title.",
    )
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of report generation.",
    )
    period_start: datetime = Field(
        ...,
        description="Start of the reporting period (UTC).",
    )
    period_end: datetime = Field(
        ...,
        description="End of the reporting period (UTC).",
    )
    total_violations: int = Field(
        ...,
        ge=0,
        description="Total number of violations in the period.",
    )
    critical_count: int = Field(default=0, ge=0)
    high_count: int = Field(default=0, ge=0)
    medium_count: int = Field(default=0, ge=0)
    low_count: int = Field(default=0, ge=0)
    compliance_score: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Weighted compliance score (100 = fully compliant).",
    )
    executive_summary: str = Field(
        ...,
        description="High-level narrative summary for executives.",
    )
    recommendations: list[str] = Field(
        default_factory=list,
        description="Actionable recommendations based on findings.",
    )
    report_hash: str = Field(
        ...,
        description="SHA-256 hash of report content for integrity verification.",
    )


def _compute_report_hash(data: dict[str, Any]) -> str:
    """Return a SHA-256 hex digest of the canonical JSON representation."""
    content = json.dumps(data, sort_keys=True, default=str)
    return hashlib.sha256(content.encode()).hexdigest()


def _calculate_compliance_score(
    critical: int,
    high: int,
    medium: int,
    low: int,
) -> float:
    """Compute a 0–100 compliance score using severity-weighted deductions."""
    deduction = (
        critical * _SEVERITY_WEIGHTS["CRITICAL"]
        + high * _SEVERITY_WEIGHTS["HIGH"]
        + medium * _SEVERITY_WEIGHTS["MEDIUM"]
        + low * _SEVERITY_WEIGHTS["LOW"]
    )
    return max(0.0, min(100.0, 100.0 - deduction))


def _generate_executive_summary(
    critical: int,
    high: int,
    medium: int,
    low: int,
    total: int,
    score: float,
) -> str:
    """Build a human-readable executive summary paragraph."""
    parts: list[str] = [
        f"During the reporting period, {total} compliance "
        f"violation{'s' if total != 1 else ''} "
        f"{'were' if total != 1 else 'was'} identified.",
        f"Breakdown: {critical} critical, {high} high, "
        f"{medium} medium, {low} low.",
        f"The overall compliance score is {score:.1f}/100.",
    ]
    if critical > 0:
        parts.append(
            "Immediate attention is required for critical violations "
            "that may impact regulatory standing."
        )
    if score >= 90.0:
        parts.append("The project maintains a strong compliance posture.")
    elif score >= 70.0:
        parts.append(
            "Compliance posture is acceptable but improvements are recommended."
        )
    else:
        parts.append(
            "Compliance posture is below acceptable thresholds; "
            "corrective action is urgently needed."
        )
    return " ".join(parts)


def _generate_recommendations(
    critical: int,
    high: int,
    medium: int,
    low: int,
) -> list[str]:
    """Produce actionable recommendations based on violation counts."""
    recs: list[str] = []
    if critical > 0:
        recs.append(
            "Conduct an emergency review of all critical violations "
            "and implement corrective actions within 24 hours."
        )
    if high > 0:
        recs.append(
            "Schedule expert review sessions for high-severity findings "
            "within the next business week."
        )
    if medium > 0:
        recs.append(
            "Enable automated remediation playbooks for medium-severity "
            "violations to reduce manual effort."
        )
    if low > 0:
        recs.append(
            "Track low-severity items in the backlog and address "
            "during routine maintenance cycles."
        )
    if not recs:
        recs.append(
            "No violations detected. Continue current compliance monitoring."
        )
    return recs


class ReportingAgent:
    """Generates compliance reports from violation data.

    On instantiation the agent subscribes to ``compliance.report_request``
    events.  Each request payload is expected to contain violation counts
    and a reporting period, from which a scored :class:`ComplianceReport`
    is produced.
    """

    def __init__(self, event_bus: EventBus) -> None:
        self._event_bus = event_bus
        self._reports: list[ComplianceReport] = []
        self._event_bus.subscribe("compliance.report_request", self.generate_report)
        logger.info('{"agent":"ReportingAgent","action":"initialized"}')

    def generate_report(self, event: ComplianceEvent) -> ComplianceReport:
        """Create a :class:`ComplianceReport` from *event* payload.

        Expected payload keys:
            - ``title`` (str): Report title.
            - ``period_start`` (str|datetime): ISO-8601 start date.
            - ``period_end`` (str|datetime): ISO-8601 end date.
            - ``violations`` (dict): Counts keyed by severity, e.g.
              ``{"CRITICAL": 2, "HIGH": 5, "MEDIUM": 10, "LOW": 20}``.

        Args:
            event: A ``compliance.report_request`` event.

        Returns:
            A frozen :class:`ComplianceReport` with SHA-256 integrity hash.
        """
        payload = event.payload
        title = str(payload.get("title", "Compliance Report"))

        period_start = _parse_datetime(payload.get("period_start"))
        period_end = _parse_datetime(payload.get("period_end"))

        violations: dict[str, int] = payload.get("violations", {})
        critical = int(violations.get("CRITICAL", 0))
        high = int(violations.get("HIGH", 0))
        medium = int(violations.get("MEDIUM", 0))
        low = int(violations.get("LOW", 0))
        total = critical + high + medium + low

        score = _calculate_compliance_score(critical, high, medium, low)
        summary = _generate_executive_summary(
            critical, high, medium, low, total, score,
        )
        recommendations = _generate_recommendations(critical, high, medium, low)

        hash_data = {
            "title": title,
            "period_start": str(period_start),
            "period_end": str(period_end),
            "critical_count": critical,
            "high_count": high,
            "medium_count": medium,
            "low_count": low,
            "total_violations": total,
            "compliance_score": score,
            "executive_summary": summary,
            "recommendations": recommendations,
        }
        report_hash = _compute_report_hash(hash_data)

        report = ComplianceReport(
            title=title,
            period_start=period_start,
            period_end=period_end,
            total_violations=total,
            critical_count=critical,
            high_count=high,
            medium_count=medium,
            low_count=low,
            compliance_score=score,
            executive_summary=summary,
            recommendations=recommendations,
            report_hash=report_hash,
        )

        self._reports.append(report)

        logger.info(
            '{"agent":"ReportingAgent","action":"report_generated",'
            '"report_id":"%s","total_violations":%d,"compliance_score":%.1f,'
            '"report_hash":"%s"}',
            report.report_id,
            total,
            score,
            report_hash,
        )

        return report


def _parse_datetime(value: Any) -> datetime:
    """Coerce *value* to a timezone-aware ``datetime``."""
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
    if isinstance(value, str):
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt
    return datetime.now(timezone.utc)
