"""Risk modeling data structures for the predictive risk scoring engine.

Defines the core Pydantic models used throughout the risk engine:
``RiskFactor``, ``RiskProfile``, and ``RiskTrend``.  All models are
frozen (immutable) to guarantee integrity once constructed.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


def compute_risk_level(score: float) -> Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]:
    """Map a numeric risk score (0-100) to a categorical risk level.

    Args:
        score: Numeric risk score in the range 0-100.

    Returns:
        One of ``LOW``, ``MEDIUM``, ``HIGH``, or ``CRITICAL``.

    Raises:
        ValueError: If *score* is outside the 0-100 range.
    """
    if score < 0 or score > 100:
        raise ValueError(f"Score must be between 0 and 100, got {score}")
    if score <= 25:
        return "LOW"
    if score <= 50:
        return "MEDIUM"
    if score <= 75:
        return "HIGH"
    return "CRITICAL"


class RiskFactor(BaseModel):
    """A single measurable risk dimension contributing to an overall profile."""

    model_config = ConfigDict(frozen=True)

    factor_id: str = Field(
        ...,
        description="Unique identifier for this risk factor.",
    )
    name: str = Field(
        ...,
        description="Human-readable name of the factor.",
    )
    category: Literal[
        "REGULATORY", "OPERATIONAL", "FINANCIAL", "SAFETY", "VENDOR"
    ] = Field(
        ...,
        description="Broad classification bucket for the factor.",
    )
    weight: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Relative importance weight (0-1).",
    )
    current_value: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Current assessed value (0-100).",
    )
    description: str = Field(
        ...,
        description="Explanation of what this factor measures.",
    )


class RiskProfile(BaseModel):
    """Aggregated risk assessment for a single entity at a point in time."""

    model_config = ConfigDict(frozen=True)

    profile_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for this profile snapshot.",
    )
    entity_id: str = Field(
        ...,
        description="Identifier of the assessed entity.",
    )
    entity_type: Literal["PROJECT", "CONTRACTOR", "VENDOR", "SITE"] = Field(
        ...,
        description="Classification of the assessed entity.",
    )
    factors: list[RiskFactor] = Field(
        ...,
        description="Individual risk factors comprising this profile.",
    )
    overall_score: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Weighted aggregate risk score (0-100).",
    )
    risk_level: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] = Field(
        ...,
        description="Categorical risk classification derived from overall_score.",
    )
    assessed_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of the assessment.",
    )
    profile_hash: str = Field(
        ...,
        description="SHA-256 digest of the profile content for integrity verification.",
    )


class RiskTrend(BaseModel):
    """Temporal trend analysis of risk scores for a single entity."""

    model_config = ConfigDict(frozen=True)

    entity_id: str = Field(
        ...,
        description="Identifier of the entity being tracked.",
    )
    scores: list[float] = Field(
        ...,
        description="Chronologically ordered risk scores.",
    )
    timestamps: list[datetime] = Field(
        ...,
        description="Timestamps corresponding to each score entry.",
    )
    trend_direction: Literal["IMPROVING", "STABLE", "DEGRADING"] = Field(
        ...,
        description="Overall direction the risk score is moving.",
    )
    change_rate: float = Field(
        ...,
        description="Average per-observation change in score (negative = improving).",
    )
