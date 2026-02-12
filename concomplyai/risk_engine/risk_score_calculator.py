"""Weighted risk score calculation and trend tracking.

``RiskScoreCalculator`` computes aggregate risk scores from individual
``RiskFactor`` instances, assembles full ``RiskProfile`` snapshots with
SHA-256 integrity hashes, and maintains per-entity score histories to
derive ``RiskTrend`` analyses.
"""

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from datetime import datetime, timezone

from concomplyai.core.event_bus import ComplianceEvent, EventBus
from concomplyai.risk_engine.risk_model import (
    RiskFactor,
    RiskProfile,
    RiskTrend,
    compute_risk_level,
)

logger = logging.getLogger(__name__)


class RiskScoreCalculator:
    """Computes risk scores, builds profiles, and tracks trends.

    An optional ``EventBus`` can be supplied at construction time; when
    present the calculator publishes ``risk.profile.created`` and
    ``risk.trend.updated`` events automatically.
    """

    def __init__(self, event_bus: EventBus | None = None) -> None:
        self._event_bus = event_bus
        self._history: dict[str, list[tuple[float, datetime]]] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def calculate_score(self, factors: list[RiskFactor]) -> float:
        """Compute a weighted-average risk score from *factors*.

        If the total weight across all factors is zero the method returns
        ``0.0`` rather than raising a division error.

        Args:
            factors: Non-empty list of ``RiskFactor`` instances.

        Returns:
            Aggregate risk score clamped to the 0-100 range.
        """
        if not factors:
            return 0.0

        total_weight = sum(f.weight for f in factors)
        if total_weight == 0.0:
            return 0.0

        weighted_sum = sum(f.weight * f.current_value for f in factors)
        score = weighted_sum / total_weight
        return round(max(0.0, min(100.0, score)), 2)

    def calculate_profile(
        self,
        entity_id: str,
        entity_type: str,
        factors: list[RiskFactor],
    ) -> RiskProfile:
        """Build a complete ``RiskProfile`` for the given entity.

        The profile includes a SHA-256 hash computed over the entity
        metadata and factor data so downstream consumers can verify
        integrity.

        Args:
            entity_id: Unique identifier for the entity being assessed.
            entity_type: One of ``PROJECT``, ``CONTRACTOR``, ``VENDOR``,
                or ``SITE``.
            factors: Risk factors to aggregate.

        Returns:
            A fully populated, immutable ``RiskProfile``.
        """
        overall_score = self.calculate_score(factors)
        risk_level = compute_risk_level(overall_score)
        assessed_at = datetime.now(timezone.utc)
        profile_id = str(uuid.uuid4())

        profile_hash = self._compute_hash(
            entity_id=entity_id,
            entity_type=entity_type,
            factors=factors,
            overall_score=overall_score,
            assessed_at=assessed_at,
        )

        profile = RiskProfile(
            profile_id=profile_id,
            entity_id=entity_id,
            entity_type=entity_type,
            factors=factors,
            overall_score=overall_score,
            risk_level=risk_level,
            assessed_at=assessed_at,
            profile_hash=profile_hash,
        )

        if self._event_bus is not None:
            self._event_bus.publish(
                ComplianceEvent(
                    event_type="risk.profile.created",
                    source="RiskScoreCalculator",
                    payload={
                        "profile_id": profile.profile_id,
                        "entity_id": entity_id,
                        "overall_score": overall_score,
                        "risk_level": risk_level,
                    },
                    severity=risk_level,
                )
            )

        logger.info(
            '{"action":"profile_created","entity_id":"%s","score":%.2f,"level":"%s"}',
            entity_id,
            overall_score,
            risk_level,
        )
        return profile

    def track_trend(self, entity_id: str, new_score: float) -> RiskTrend:
        """Record *new_score* and return the updated ``RiskTrend``.

        Scores are stored in chronological order.  The trend direction
        and change rate are recalculated on every call.

        Args:
            entity_id: The entity whose score history to update.
            new_score: Latest risk score observation.

        Returns:
            Current ``RiskTrend`` reflecting all recorded observations.
        """
        now = datetime.now(timezone.utc)
        history = self._history.setdefault(entity_id, [])
        history.append((new_score, now))

        scores = [s for s, _ in history]
        timestamps = [t for _, t in history]
        trend_direction, change_rate = self._determine_trend(scores)

        trend = RiskTrend(
            entity_id=entity_id,
            scores=scores,
            timestamps=timestamps,
            trend_direction=trend_direction,
            change_rate=change_rate,
        )

        if self._event_bus is not None:
            self._event_bus.publish(
                ComplianceEvent(
                    event_type="risk.trend.updated",
                    source="RiskScoreCalculator",
                    payload={
                        "entity_id": entity_id,
                        "trend_direction": trend_direction,
                        "change_rate": change_rate,
                        "observation_count": len(scores),
                    },
                )
            )

        return trend

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _determine_trend(
        self, scores: list[float]
    ) -> tuple[str, float]:
        """Analyse recent scores to derive trend direction and rate.

        Uses a simple comparison of the last three observations (or
        fewer if not enough history exists).  A positive average change
        means the score is rising (``DEGRADING``); negative means it is
        falling (``IMPROVING``).  Changes within ±1.0 are treated as
        ``STABLE``.

        Args:
            scores: Chronologically ordered score history.

        Returns:
            Tuple of ``(trend_direction, change_rate)``.
        """
        if len(scores) < 2:
            return ("STABLE", 0.0)

        recent = scores[-3:] if len(scores) >= 3 else scores
        deltas = [recent[i] - recent[i - 1] for i in range(1, len(recent))]
        change_rate = round(sum(deltas) / len(deltas), 4)

        if change_rate > 1.0:
            return ("DEGRADING", change_rate)
        if change_rate < -1.0:
            return ("IMPROVING", change_rate)
        return ("STABLE", change_rate)

    @staticmethod
    def _compute_hash(
        *,
        entity_id: str,
        entity_type: str,
        factors: list[RiskFactor],
        overall_score: float,
        assessed_at: datetime,
    ) -> str:
        """Produce a SHA-256 hex digest over the canonical profile data.

        Args:
            entity_id: Entity identifier.
            entity_type: Entity classification.
            factors: Risk factors included in the profile.
            overall_score: Computed aggregate score.
            assessed_at: Assessment timestamp.

        Returns:
            Lowercase hex-encoded SHA-256 hash string.
        """
        canonical = json.dumps(
            {
                "entity_id": entity_id,
                "entity_type": entity_type,
                "factors": [f.model_dump(mode="json") for f in factors],
                "overall_score": overall_score,
                "assessed_at": assessed_at.isoformat(),
            },
            sort_keys=True,
            default=str,
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
