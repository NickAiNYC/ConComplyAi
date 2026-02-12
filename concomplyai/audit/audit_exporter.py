"""Audit Exporter — export decision logs for regulatory review.

Provides JSON export and summary statistics with SHA-256 integrity hashes.
PDF export is listed as a planned feature and currently raises
``NotImplementedError``.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from concomplyai.audit.decision_logger import DecisionLogger


def _compute_summary_hash(
    total_decisions: int,
    decisions_by_agent: dict[str, int],
    average_confidence: float,
    date_range_start: datetime | None,
    date_range_end: datetime | None,
    generated_at: datetime,
) -> str:
    """Compute SHA-256 over summary fields for integrity verification."""
    canonical = json.dumps(
        {
            "total_decisions": total_decisions,
            "decisions_by_agent": decisions_by_agent,
            "average_confidence": average_confidence,
            "date_range_start": date_range_start.isoformat() if date_range_start else None,
            "date_range_end": date_range_end.isoformat() if date_range_end else None,
            "generated_at": generated_at.isoformat(),
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class AuditSummary(BaseModel):
    """Immutable statistical summary of logged decisions."""

    model_config = ConfigDict(frozen=True)

    total_decisions: int = Field(description="Total number of decisions in the export window.")
    decisions_by_agent: dict[str, int] = Field(description="Decision count keyed by agent name.")
    average_confidence: float = Field(description="Mean confidence across all decisions.")
    date_range_start: datetime | None = Field(description="Earliest decision timestamp, or None.")
    date_range_end: datetime | None = Field(description="Latest decision timestamp, or None.")
    generated_at: datetime = Field(description="UTC timestamp when the summary was generated.")
    summary_hash: str = Field(description="SHA-256 hash for tamper detection.")


class AuditExporter:
    """Export decision logs to JSON and summary formats.

    Args:
        logger: ``DecisionLogger`` instance to read decisions from.
    """

    def __init__(self, logger: DecisionLogger) -> None:
        self._logger = logger

    def export_json(
        self,
        agent_name: str | None = None,
        limit: int = 1000,
    ) -> str:
        """Serialize decisions to a JSON string.

        Args:
            agent_name: If provided, only export decisions from this agent.
            limit: Maximum number of decisions to include.

        Returns:
            A JSON-formatted string of decision records.
        """
        entries = self._logger.get_decisions(agent_name=agent_name, limit=limit)
        records: list[dict[str, Any]] = []
        for entry in entries:
            records.append(
                {
                    "decision_id": entry.decision_id,
                    "agent_name": entry.agent_name,
                    "decision": entry.decision,
                    "reasoning": entry.reasoning,
                    "confidence": entry.confidence,
                    "input_summary": entry.input_summary,
                    "timestamp": entry.timestamp.isoformat(),
                    "metadata": entry.metadata,
                    "entry_hash": entry.entry_hash,
                }
            )
        return json.dumps(records, indent=2)

    def export_summary(
        self,
        agent_name: str | None = None,
    ) -> AuditSummary:
        """Generate aggregate statistics over logged decisions.

        Args:
            agent_name: If provided, restrict the summary to this agent.

        Returns:
            A frozen ``AuditSummary`` model with SHA-256 integrity hash.
        """
        entries = self._logger.get_decisions(agent_name=agent_name, limit=0)
        # limit=0 edge: fetch all by using a very large limit
        entries = self._logger.get_decisions(agent_name=agent_name, limit=10_000_000)

        total = len(entries)
        by_agent: dict[str, int] = {}
        confidence_sum = 0.0
        earliest: datetime | None = None
        latest: datetime | None = None

        for entry in entries:
            by_agent[entry.agent_name] = by_agent.get(entry.agent_name, 0) + 1
            confidence_sum += entry.confidence
            if earliest is None or entry.timestamp < earliest:
                earliest = entry.timestamp
            if latest is None or entry.timestamp > latest:
                latest = entry.timestamp

        avg_confidence = confidence_sum / total if total > 0 else 0.0
        generated_at = datetime.now(timezone.utc)

        summary_hash = _compute_summary_hash(
            total_decisions=total,
            decisions_by_agent=by_agent,
            average_confidence=avg_confidence,
            date_range_start=earliest,
            date_range_end=latest,
            generated_at=generated_at,
        )

        return AuditSummary(
            total_decisions=total,
            decisions_by_agent=by_agent,
            average_confidence=avg_confidence,
            date_range_start=earliest,
            date_range_end=latest,
            generated_at=generated_at,
            summary_hash=summary_hash,
        )

    def export_pdf(
        self,
        agent_name: str | None = None,
        limit: int = 1000,
    ) -> bytes:
        """Export decisions as a PDF document.

        This feature is planned but not yet implemented. PDF generation
        requires additional dependencies (e.g. ``reportlab`` or ``weasyprint``)
        that are not currently included in the project.

        Raises:
            NotImplementedError: Always raised until PDF support is added.
        """
        raise NotImplementedError(
            "PDF export is not yet implemented. Use export_json() for machine-readable "
            "output or export_summary() for aggregate statistics. PDF support will require "
            "an additional dependency such as 'reportlab' or 'weasyprint'."
        )
