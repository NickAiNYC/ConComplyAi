"""Tests for concomplyai.vendor_risk (vendor_scoring, vendor_dashboard).

Covers vendor risk scoring based on certifications and compliance
history, score hash integrity, and the vendor dashboard's exposure
summary and reporting capabilities.
"""

import re
from datetime import datetime, timedelta, timezone

import pytest

from concomplyai.core.event_bus import EventBus
from concomplyai.vendor_risk.vendor_profile import (
    ComplianceRecord,
    VendorCertification,
    VendorProfile,
)
from concomplyai.vendor_risk.vendor_scoring import VendorRiskScorer
from concomplyai.vendor_risk.vendor_dashboard import VendorDashboard


SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")

_NOW = datetime.now(timezone.utc)
_FUTURE = _NOW + timedelta(days=365)
_PAST = _NOW - timedelta(days=30)


def _valid_cert(cert_id: str = "CERT-1", name: str = "ISO 9001") -> VendorCertification:
    return VendorCertification(
        cert_id=cert_id,
        name=name,
        issuing_body="ISO",
        issue_date=_NOW - timedelta(days=180),
        expiry_date=_FUTURE,
        is_valid=True,
    )


def _expired_cert(cert_id: str = "CERT-EXP", name: str = "ISO 14001") -> VendorCertification:
    return VendorCertification(
        cert_id=cert_id,
        name=name,
        issuing_body="ISO",
        issue_date=_NOW - timedelta(days=730),
        expiry_date=_PAST,
        is_valid=False,
    )


def _pass_record(record_id: str = "REC-1", category: str = "SAFETY") -> ComplianceRecord:
    return ComplianceRecord(
        record_id=record_id,
        check_date=_NOW,
        passed=True,
        category=category,
        details="All checks passed.",
    )


def _fail_record(record_id: str = "REC-F", category: str = "ENVIRONMENTAL") -> ComplianceRecord:
    return ComplianceRecord(
        record_id=record_id,
        check_date=_NOW,
        passed=False,
        category=category,
        details="Emission limits exceeded.",
    )


def _make_profile(
    vendor_id: str = "V-001",
    company_name: str = "Acme Corp",
    certifications: list | None = None,
    compliance_history: list | None = None,
) -> VendorProfile:
    return VendorProfile(
        vendor_id=vendor_id,
        company_name=company_name,
        industry="Construction",
        certifications=certifications or [],
        compliance_history=compliance_history or [],
        contact_email="vendor@example.com",
    )


class TestVendorScoring:
    """Tests for the VendorRiskScorer."""

    @pytest.fixture
    def scorer(self):
        return VendorRiskScorer()

    def test_vendor_all_valid_certs_scores_well(self, scorer):
        """Vendor with valid certs and passing compliance should score high."""
        profile = _make_profile(
            certifications=[_valid_cert("C1"), _valid_cert("C2", "OSHA 30")],
            compliance_history=[_pass_record("R1"), _pass_record("R2")],
        )
        score = scorer.score_vendor(profile)

        assert score.certification_score == 100.0
        assert score.compliance_score == 100.0
        assert score.overall_score >= 80.0
        assert score.risk_level == "LOW"

    def test_vendor_expired_certs_scores_poorly(self, scorer):
        """Vendor with all expired certs should have low certification score."""
        profile = _make_profile(
            certifications=[_expired_cert("C1"), _expired_cert("C2", "OSHA Exp")],
            compliance_history=[_pass_record()],
        )
        score = scorer.score_vendor(profile)

        assert score.certification_score == 0.0
        assert any("Expired" in f for f in score.risk_factors)

    def test_vendor_failed_compliance_checks(self, scorer):
        """Vendor with failed checks should have reduced compliance score."""
        profile = _make_profile(
            certifications=[_valid_cert()],
            compliance_history=[_pass_record("R1"), _fail_record("R2")],
        )
        score = scorer.score_vendor(profile)

        assert score.compliance_score == 50.0
        assert any("Failed" in f for f in score.risk_factors)

    def test_score_hash_integrity(self, scorer):
        """Score hash must be a valid 64-char hex SHA-256 string."""
        profile = _make_profile(
            certifications=[_valid_cert()],
            compliance_history=[_pass_record()],
        )
        score = scorer.score_vendor(profile)
        assert SHA256_PATTERN.match(score.score_hash)


class TestVendorDashboard:
    """Tests for the VendorDashboard."""

    @pytest.fixture
    def bus(self):
        return EventBus()

    @pytest.fixture
    def dashboard(self, bus):
        return VendorDashboard(bus)

    def test_add_vendor_and_get_exposure_summary(self, dashboard):
        """Adding a vendor should be reflected in the exposure summary."""
        profile = _make_profile(
            certifications=[_valid_cert()],
            compliance_history=[_pass_record()],
        )
        dashboard.add_vendor(profile)

        summary = dashboard.get_exposure_summary()
        assert summary.total_vendors == 1
        assert summary.average_score > 0

    def test_get_vendor_report(self, dashboard):
        """get_vendor_report should return a populated VendorReport."""
        profile = _make_profile(
            vendor_id="V-RPT",
            certifications=[_valid_cert(), _expired_cert()],
            compliance_history=[_pass_record(), _fail_record()],
        )
        dashboard.add_vendor(profile)

        report = dashboard.get_vendor_report("V-RPT")
        assert report is not None
        assert report.vendor_id == "V-RPT"
        assert report.active_certifications == 1
        assert report.expired_certifications == 1
        assert report.compliance_pass_rate == 50.0

    def test_get_vendor_report_nonexistent_returns_none(self, dashboard):
        """Requesting a report for an unknown vendor should return None."""
        assert dashboard.get_vendor_report("UNKNOWN") is None

    def test_exposure_summary_empty_dashboard(self, dashboard):
        """Empty dashboard should produce zero-valued summary."""
        summary = dashboard.get_exposure_summary()
        assert summary.total_vendors == 0
        assert summary.average_score == 0.0
