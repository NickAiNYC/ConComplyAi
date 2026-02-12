"""Vendor risk dashboard for aggregate exposure reporting.

Maintains a collection of scored vendor profiles and produces summary
reports with actionable recommendations, publishing events via the
shared ``EventBus``.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from concomplyai.core.event_bus import ComplianceEvent, EventBus
from concomplyai.vendor_risk.vendor_profile import VendorProfile
from concomplyai.vendor_risk.vendor_scoring import VendorRiskScore, VendorRiskScorer

logger = logging.getLogger(__name__)


class ExposureSummary(BaseModel):
    """Immutable aggregate summary of vendor risk exposure."""

    model_config = ConfigDict(frozen=True)

    total_vendors: int = Field(
        ...,
        description="Total number of vendors tracked.",
    )
    high_risk_count: int = Field(
        ...,
        description="Number of vendors classified as HIGH risk.",
    )
    critical_risk_count: int = Field(
        ...,
        description="Number of vendors classified as CRITICAL risk.",
    )
    average_score: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Mean overall score across all vendors.",
    )
    top_risks: list[str] = Field(
        default_factory=list,
        description="Most significant risk factors across the vendor portfolio.",
    )
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when the summary was generated.",
    )


class VendorReport(BaseModel):
    """Immutable risk report for a single vendor."""

    model_config = ConfigDict(frozen=True)

    vendor_id: str = Field(
        ...,
        description="Unique identifier of the reported vendor.",
    )
    company_name: str = Field(
        ...,
        description="Legal company name.",
    )
    overall_score: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Weighted aggregate risk score.",
    )
    risk_level: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] = Field(
        ...,
        description="Categorical risk classification.",
    )
    active_certifications: int = Field(
        ...,
        ge=0,
        description="Count of currently valid certifications.",
    )
    expired_certifications: int = Field(
        ...,
        ge=0,
        description="Count of expired certifications.",
    )
    compliance_pass_rate: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Percentage of compliance checks passed.",
    )
    recommendations: list[str] = Field(
        default_factory=list,
        description="Actionable recommendations for risk reduction.",
    )


def _generate_recommendations(
    profile: VendorProfile,
    score: VendorRiskScore,
) -> list[str]:
    """Produce actionable recommendations based on profile and score.

    Args:
        profile: The vendor profile.
        score: The computed risk score.

    Returns:
        List of recommendation strings.
    """
    recommendations: list[str] = []

    expired = [c for c in profile.certifications if not c.is_valid]
    if expired:
        names = ", ".join(c.name for c in expired)
        recommendations.append(f"Renew expired certifications: {names}")

    if not profile.certifications:
        recommendations.append("Obtain industry-standard certifications")

    failed = [r for r in profile.compliance_history if not r.passed]
    if failed:
        categories = sorted({r.category for r in failed})
        recommendations.append(
            f"Address compliance failures in: {', '.join(categories)}"
        )

    if not profile.compliance_history:
        recommendations.append("Conduct initial compliance assessment")

    if score.risk_level == "CRITICAL":
        recommendations.append(
            "Escalate to senior management for immediate review"
        )
    elif score.risk_level == "HIGH":
        recommendations.append("Schedule priority review within 30 days")

    if score.certification_score < 50.0 and profile.certifications:
        recommendations.append(
            "More than half of certifications are expired; prioritise renewal"
        )

    if score.compliance_score < 50.0 and profile.compliance_history:
        recommendations.append(
            "Compliance pass rate is below 50 %; implement corrective action plan"
        )

    return recommendations


class VendorDashboard:
    """Aggregates vendor risk data and exposes reporting methods.

    Publishes events on the shared ``EventBus`` when vendors are added
    or exposure summaries are generated.
    """

    def __init__(self, event_bus: EventBus) -> None:
        """Initialise the dashboard with an event bus.

        Args:
            event_bus: Shared event bus for publishing vendor risk events.
        """
        self._event_bus = event_bus
        self._scorer = VendorRiskScorer()
        self._vendors: dict[str, VendorProfile] = {}
        self._scores: dict[str, VendorRiskScore] = {}

    def add_vendor(self, profile: VendorProfile) -> None:
        """Add a vendor profile and compute its risk score.

        Publishes a ``vendor_risk.vendor_added`` event on success.

        Args:
            profile: The vendor profile to register.
        """
        score = self._scorer.score_vendor(profile)
        self._vendors[profile.vendor_id] = profile
        self._scores[profile.vendor_id] = score

        self._event_bus.publish(
            ComplianceEvent(
                event_type="vendor_risk.vendor_added",
                source="VendorDashboard",
                payload={
                    "vendor_id": profile.vendor_id,
                    "company_name": profile.company_name,
                    "risk_level": score.risk_level,
                    "overall_score": score.overall_score,
                },
                severity=score.risk_level,
            )
        )

        logger.info(
            '{"action":"vendor_added","vendor_id":"%s","risk_level":"%s"}',
            profile.vendor_id,
            score.risk_level,
        )

    def get_exposure_summary(self) -> ExposureSummary:
        """Summarise risk exposure across all tracked vendors.

        Publishes a ``vendor_risk.exposure_summary`` event.

        Returns:
            An ``ExposureSummary`` snapshot.
        """
        total = len(self._scores)
        if total == 0:
            summary = ExposureSummary(
                total_vendors=0,
                high_risk_count=0,
                critical_risk_count=0,
                average_score=0.0,
                top_risks=[],
            )
            return summary

        high_count = sum(
            1 for s in self._scores.values() if s.risk_level == "HIGH"
        )
        critical_count = sum(
            1 for s in self._scores.values() if s.risk_level == "CRITICAL"
        )
        avg_score = round(
            sum(s.overall_score for s in self._scores.values()) / total, 2
        )

        all_factors: list[str] = []
        for s in self._scores.values():
            all_factors.extend(s.risk_factors)
        top_risks = sorted(set(all_factors))[:10]

        summary = ExposureSummary(
            total_vendors=total,
            high_risk_count=high_count,
            critical_risk_count=critical_count,
            average_score=avg_score,
            top_risks=top_risks,
        )

        self._event_bus.publish(
            ComplianceEvent(
                event_type="vendor_risk.exposure_summary",
                source="VendorDashboard",
                payload={
                    "total_vendors": summary.total_vendors,
                    "high_risk_count": summary.high_risk_count,
                    "critical_risk_count": summary.critical_risk_count,
                    "average_score": summary.average_score,
                },
                severity="HIGH" if critical_count > 0 else "LOW",
            )
        )

        return summary

    def get_vendor_report(self, vendor_id: str) -> VendorReport | None:
        """Generate a detailed report for a single vendor.

        Args:
            vendor_id: Identifier of the vendor to report on.

        Returns:
            A ``VendorReport`` if the vendor exists, otherwise ``None``.
        """
        profile = self._vendors.get(vendor_id)
        score = self._scores.get(vendor_id)
        if profile is None or score is None:
            return None

        active_certs = sum(1 for c in profile.certifications if c.is_valid)
        expired_certs = len(profile.certifications) - active_certs

        total_checks = len(profile.compliance_history)
        passed_checks = sum(1 for r in profile.compliance_history if r.passed)
        pass_rate = round(
            (passed_checks / total_checks * 100.0) if total_checks > 0 else 0.0,
            2,
        )

        recommendations = _generate_recommendations(profile, score)

        return VendorReport(
            vendor_id=profile.vendor_id,
            company_name=profile.company_name,
            overall_score=score.overall_score,
            risk_level=score.risk_level,
            active_certifications=active_certs,
            expired_certifications=expired_certs,
            compliance_pass_rate=pass_rate,
            recommendations=recommendations,
        )
