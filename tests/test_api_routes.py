"""Tests for concomplyai.api routes via FastAPI TestClient.

Covers health, compliance, risk, vendor, and audit endpoints.
Module-level singletons in routes are reset between tests to ensure
isolation.
"""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from concomplyai.api.app import create_app


@pytest.fixture(autouse=True)
def _reset_route_singletons():
    """Reset lazy singletons in routes module between tests."""
    from concomplyai.api import routes

    routes._event_bus = None
    routes._reporting_agent = None
    routes._monitoring_agent = None
    routes._risk_calculator = None
    routes._scenario_simulator = None
    routes._vendor_dashboard = None
    routes._decision_logger = None
    routes._audit_exporter = None
    yield


@pytest.fixture
def client():
    """Create a fresh TestClient with no auth token configured."""
    import os
    os.environ["CONCOMPLYAI_AUTH_TOKEN"] = ""
    # Clear cached settings so the empty token takes effect
    from concomplyai.config.settings import get_settings
    get_settings.cache_clear()
    app = create_app()
    with TestClient(app) as c:
        yield c
    get_settings.cache_clear()


_NOW = datetime.now(timezone.utc)
_FUTURE = _NOW + timedelta(days=365)
_PAST = _NOW - timedelta(days=30)


class TestHealthEndpoint:
    """Tests for GET /health."""

    def test_health_returns_200(self, client):
        """Health endpoint should return 200 with status healthy."""
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert "version" in data


class TestComplianceEndpoints:
    """Tests for compliance report and score endpoints."""

    def test_post_compliance_report(self, client):
        """POST /compliance/report should return a generated report."""
        body = {
            "title": "Test Report",
            "period_start": "2025-01-01T00:00:00Z",
            "period_end": "2025-03-31T23:59:59Z",
            "violations": {"CRITICAL": 1, "HIGH": 2, "MEDIUM": 3, "LOW": 4},
        }
        resp = client.post("/compliance/report", json=body)
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "Test Report"
        assert data["total_violations"] == 10
        assert "compliance_score" in data
        assert "report_hash" in data

    def test_get_compliance_score(self, client):
        """GET /compliance/score should return monitoring metrics."""
        resp = client.get("/compliance/score")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_events" in data
        assert "events_by_type" in data


class TestRiskEndpoints:
    """Tests for risk calculation and simulation endpoints."""

    def _risk_factor(self, factor_id="F1", value=50.0):
        return {
            "factor_id": factor_id,
            "name": f"Factor {factor_id}",
            "category": "REGULATORY",
            "weight": 0.5,
            "current_value": value,
            "description": f"Test factor {factor_id}",
        }

    def test_post_risk_calculate(self, client):
        """POST /risk/calculate should return a risk profile."""
        body = {
            "entity_id": "PROJ-001",
            "entity_type": "PROJECT",
            "factors": [self._risk_factor("F1", 60.0)],
        }
        resp = client.post("/risk/calculate", json=body)
        assert resp.status_code == 200
        data = resp.json()
        assert data["entity_id"] == "PROJ-001"
        assert "overall_score" in data
        assert "risk_level" in data
        assert "profile_hash" in data

    def test_post_risk_simulate(self, client):
        """POST /risk/simulate should return a simulation result."""
        body = {
            "base_entity_id": "PROJ-SIM",
            "base_entity_type": "PROJECT",
            "base_factors": [
                self._risk_factor("F1", 60.0),
                self._risk_factor("F2", 40.0),
            ],
            "scenario": {
                "name": "What-if",
                "description": "Lower F1",
                "factor_adjustments": {"F1": 20.0},
            },
        }
        resp = client.post("/risk/simulate", json=body)
        assert resp.status_code == 200
        data = resp.json()
        assert "original_score" in data
        assert "projected_score" in data
        assert "score_delta" in data


class TestVendorEndpoints:
    """Tests for vendor add, exposure, and report endpoints."""

    def _vendor_body(self, vendor_id="V-API"):
        return {
            "vendor_id": vendor_id,
            "company_name": "API Test Corp",
            "industry": "Construction",
            "certifications": [
                {
                    "cert_id": "C1",
                    "name": "ISO 9001",
                    "issuing_body": "ISO",
                    "issue_date": (_NOW - timedelta(days=180)).isoformat(),
                    "expiry_date": _FUTURE.isoformat(),
                    "is_valid": True,
                }
            ],
            "compliance_history": [
                {
                    "record_id": "R1",
                    "check_date": _NOW.isoformat(),
                    "passed": True,
                    "category": "SAFETY",
                    "details": "All clear.",
                }
            ],
            "contact_email": "api@test.com",
        }

    def test_add_vendor(self, client):
        """POST /vendor/add should register a vendor."""
        resp = client.post("/vendor/add", json=self._vendor_body())
        assert resp.status_code == 200
        assert resp.json()["status"] == "added"

    def test_get_vendor_exposure(self, client):
        """GET /vendor/exposure should return an exposure summary."""
        resp = client.get("/vendor/exposure")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_vendors" in data

    def test_get_vendor_report(self, client):
        """GET /vendor/{id} should return a vendor report after adding."""
        client.post("/vendor/add", json=self._vendor_body("V-RPT"))
        resp = client.get("/vendor/V-RPT")
        assert resp.status_code == 200
        data = resp.json()
        assert data["vendor_id"] == "V-RPT"

    def test_get_vendor_report_not_found(self, client):
        """GET /vendor/{id} for unknown vendor should return 404."""
        resp = client.get("/vendor/UNKNOWN")
        assert resp.status_code == 404


class TestAuditEndpoints:
    """Tests for audit decision listing, summary, and export endpoints."""

    def test_list_audit_decisions_empty(self, client):
        """GET /audit/decisions with no logged decisions returns empty list."""
        resp = client.get("/audit/decisions")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_get_audit_summary(self, client):
        """GET /audit/summary should return aggregate statistics."""
        resp = client.get("/audit/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_decisions" in data
        assert data["total_decisions"] == 0

    def test_export_audit_log(self, client):
        """GET /audit/export should return a JSON list."""
        resp = client.get("/audit/export")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
