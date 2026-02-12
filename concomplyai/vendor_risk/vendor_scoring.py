"""Vendor risk scoring engine.

Computes risk scores for vendor profiles based on certification validity
and compliance history, producing an integrity-hashed ``VendorRiskScore``.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from concomplyai.vendor_risk.vendor_profile import VendorProfile


class VendorRiskScore(BaseModel):
    """Immutable, integrity-hashed risk score for a single vendor."""

    model_config = ConfigDict(frozen=True)

    score_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for this score snapshot.",
    )
    vendor_id: str = Field(
        ...,
        description="Identifier of the scored vendor.",
    )
    overall_score: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Weighted aggregate score (0-100, higher is better).",
    )
    certification_score: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Score derived from certification validity (0-100).",
    )
    compliance_score: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Score derived from compliance pass rate (0-100).",
    )
    risk_level: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] = Field(
        ...,
        description="Categorical risk classification.",
    )
    risk_factors: list[str] = Field(
        default_factory=list,
        description="Specific risk issues identified during scoring.",
    )
    scored_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when the score was computed.",
    )
    score_hash: str = Field(
        ...,
        description="SHA-256 digest of score content for integrity verification.",
    )


def _compute_risk_level(score: float) -> Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]:
    """Map a numeric score (0-100) to a categorical risk level.

    Higher scores indicate better compliance, so lower scores yield
    higher risk classifications.

    Args:
        score: Numeric score in the range 0-100.

    Returns:
        Categorical risk level string.
    """
    if score >= 80.0:
        return "LOW"
    if score >= 60.0:
        return "MEDIUM"
    if score >= 40.0:
        return "HIGH"
    return "CRITICAL"


def _compute_score_hash(
    vendor_id: str,
    overall_score: float,
    certification_score: float,
    compliance_score: float,
    risk_level: str,
    risk_factors: list[str],
) -> str:
    """Produce a SHA-256 digest for score integrity verification.

    Args:
        vendor_id: Vendor identifier.
        overall_score: Weighted aggregate score.
        certification_score: Certification-derived score.
        compliance_score: Compliance-derived score.
        risk_level: Categorical risk level.
        risk_factors: List of identified risk issues.

    Returns:
        Hex-encoded SHA-256 hash string.
    """
    content = json.dumps(
        {
            "vendor_id": vendor_id,
            "overall_score": overall_score,
            "certification_score": certification_score,
            "compliance_score": compliance_score,
            "risk_level": risk_level,
            "risk_factors": risk_factors,
        },
        sort_keys=True,
    )
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


class VendorRiskScorer:
    """Computes risk scores for vendor profiles.

    Scoring logic:
      * **Certification score** – 100 if all certifications are valid;
        reduced proportionally for each expired or missing certification.
      * **Compliance score** – percentage of passed compliance checks.
      * **Overall score** – weighted average (40 % certification,
        60 % compliance).
    """

    CERT_WEIGHT: float = 0.4
    COMPLIANCE_WEIGHT: float = 0.6

    def score_vendor(self, profile: VendorProfile) -> VendorRiskScore:
        """Compute a risk score for the given vendor profile.

        Args:
            profile: The vendor profile to evaluate.

        Returns:
            An immutable ``VendorRiskScore`` with integrity hash.
        """
        risk_factors: list[str] = []

        certification_score = self._score_certifications(profile, risk_factors)
        compliance_score = self._score_compliance(profile, risk_factors)

        overall_score = round(
            self.CERT_WEIGHT * certification_score
            + self.COMPLIANCE_WEIGHT * compliance_score,
            2,
        )
        risk_level = _compute_risk_level(overall_score)

        score_hash = _compute_score_hash(
            vendor_id=profile.vendor_id,
            overall_score=overall_score,
            certification_score=certification_score,
            compliance_score=compliance_score,
            risk_level=risk_level,
            risk_factors=risk_factors,
        )

        return VendorRiskScore(
            vendor_id=profile.vendor_id,
            overall_score=overall_score,
            certification_score=certification_score,
            compliance_score=compliance_score,
            risk_level=risk_level,
            risk_factors=risk_factors,
            score_hash=score_hash,
        )

    def _score_certifications(
        self, profile: VendorProfile, risk_factors: list[str]
    ) -> float:
        """Score certification validity and populate risk factors.

        Args:
            profile: Vendor profile being scored.
            risk_factors: Mutable list to append risk factor strings to.

        Returns:
            Certification score (0-100).
        """
        certs = profile.certifications
        if not certs:
            risk_factors.append("No certifications on file")
            return 0.0

        valid_count = 0
        for cert in certs:
            if cert.is_valid:
                valid_count += 1
            else:
                risk_factors.append(f"Expired certification: {cert.name}")

        return round((valid_count / len(certs)) * 100.0, 2)

    def _score_compliance(
        self, profile: VendorProfile, risk_factors: list[str]
    ) -> float:
        """Score compliance history and populate risk factors.

        Args:
            profile: Vendor profile being scored.
            risk_factors: Mutable list to append risk factor strings to.

        Returns:
            Compliance score (0-100).
        """
        records = profile.compliance_history
        if not records:
            risk_factors.append("No compliance history available")
            return 0.0

        passed_count = 0
        for record in records:
            if record.passed:
                passed_count += 1
            else:
                risk_factors.append(
                    f"Failed compliance check: {record.category} - {record.details}"
                )

        return round((passed_count / len(records)) * 100.0, 2)
