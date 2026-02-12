"""Decision Logger — cryptographic audit trail for every compliance decision.

Records each agent decision as an immutable ``DecisionLogEntry`` with SHA-256
integrity hash and publishes ``audit.decision.logged`` events via the
``EventBus`` so downstream consumers (dashboards, alerting) can react in
real time.
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

_INPUT_SUMMARY_MAX_LEN = 256


def _compute_entry_hash(
    decision_id: str,
    agent_name: str,
    decision: str,
    reasoning: str,
    confidence: float,
    input_summary: str,
    timestamp: datetime,
    metadata: dict[str, Any],
) -> str:
    """Compute a deterministic SHA-256 hash over the entry's content fields."""
    canonical = json.dumps(
        {
            "decision_id": decision_id,
            "agent_name": agent_name,
            "decision": decision,
            "reasoning": reasoning,
            "confidence": confidence,
            "input_summary": input_summary,
            "timestamp": timestamp.isoformat(),
            "metadata": metadata,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _truncate_input(input_data: dict[str, Any]) -> str:
    """Return a truncated string representation of *input_data*."""
    raw = json.dumps(input_data, sort_keys=True, default=str)
    if len(raw) <= _INPUT_SUMMARY_MAX_LEN:
        return raw
    return raw[: _INPUT_SUMMARY_MAX_LEN - 3] + "..."


class DecisionLogEntry(BaseModel):
    """Immutable record of a single compliance decision."""

    model_config = ConfigDict(frozen=True)

    decision_id: str = Field(description="Unique identifier (UUID) for this decision.")
    agent_name: str = Field(description="Name of the agent that made the decision.")
    decision: str = Field(description="Decision outcome, e.g. PASS / FAIL / PENDING_HUMAN_REVIEW.")
    reasoning: str = Field(description="Human-readable explanation of the decision.")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score between 0 and 1.")
    input_summary: str = Field(description="Truncated JSON representation of the input data.")
    timestamp: datetime = Field(description="UTC timestamp when the decision was recorded.")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Arbitrary metadata.")
    entry_hash: str = Field(description="SHA-256 hash for tamper detection.")


class DecisionLogger:
    """Append-only decision log with SHA-256 integrity hashes.

    Every logged decision is stored in memory and an ``audit.decision.logged``
    event is published on the supplied ``EventBus``.
    """

    def __init__(self, event_bus: EventBus) -> None:
        self._event_bus = event_bus
        self._entries: list[DecisionLogEntry] = []
        self._index: dict[str, DecisionLogEntry] = {}

    def log_decision(
        self,
        agent_name: str,
        decision: str,
        reasoning: str,
        confidence: float,
        input_data: dict[str, Any],
        metadata: dict[str, Any] | None = None,
    ) -> DecisionLogEntry:
        """Record a compliance decision and return its immutable log entry.

        Args:
            agent_name: Agent that produced the decision.
            decision: Outcome string (e.g. ``"PASS"``, ``"FAIL"``).
            reasoning: Free-text explanation.
            confidence: Float in ``[0, 1]``.
            input_data: Raw input dict (will be truncated for storage).
            metadata: Optional extra metadata.

        Returns:
            The newly created ``DecisionLogEntry``.
        """
        resolved_metadata: dict[str, Any] = metadata if metadata is not None else {}
        decision_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc)
        input_summary = _truncate_input(input_data)

        entry_hash = _compute_entry_hash(
            decision_id=decision_id,
            agent_name=agent_name,
            decision=decision,
            reasoning=reasoning,
            confidence=confidence,
            input_summary=input_summary,
            timestamp=timestamp,
            metadata=resolved_metadata,
        )

        entry = DecisionLogEntry(
            decision_id=decision_id,
            agent_name=agent_name,
            decision=decision,
            reasoning=reasoning,
            confidence=confidence,
            input_summary=input_summary,
            timestamp=timestamp,
            metadata=resolved_metadata,
            entry_hash=entry_hash,
        )

        self._entries.append(entry)
        self._index[decision_id] = entry

        self._event_bus.publish(
            ComplianceEvent(
                event_type="audit.decision.logged",
                source="DecisionLogger",
                payload={
                    "decision_id": decision_id,
                    "agent_name": agent_name,
                    "decision": decision,
                    "confidence": confidence,
                },
                severity="LOW",
            )
        )

        logger.info(
            '{"action":"decision_logged","decision_id":"%s","agent":"%s","decision":"%s"}',
            decision_id,
            agent_name,
            decision,
        )

        return entry

    def get_decisions(
        self,
        agent_name: str | None = None,
        limit: int = 100,
    ) -> list[DecisionLogEntry]:
        """Return logged decisions, optionally filtered by agent name.

        Args:
            agent_name: If provided, only return entries from this agent.
            limit: Maximum number of entries to return (most recent first).

        Returns:
            List of ``DecisionLogEntry`` objects.
        """
        entries = self._entries
        if agent_name is not None:
            entries = [e for e in entries if e.agent_name == agent_name]
        return list(reversed(entries[-limit:]))

    def get_decision_by_id(self, decision_id: str) -> DecisionLogEntry | None:
        """Look up a single decision by its unique ID.

        Args:
            decision_id: UUID string of the decision.

        Returns:
            The matching ``DecisionLogEntry``, or ``None`` if not found.
        """
        return self._index.get(decision_id)
