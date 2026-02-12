"""API route definitions for the ConComplyAI platform."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Literal, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from concomplyai import __version__
from concomplyai.audit.audit_exporter import AuditExporter
from concomplyai.audit.decision_logger import DecisionLogger
from concomplyai.core.event_bus import ComplianceEvent, EventBus
from concomplyai.agents.monitoring_agent import MonitoringAgent
from concomplyai.agents.reporting_agent import ReportingAgent
from concomplyai.risk_engine.risk_model import RiskFactor
from concomplyai.risk_engine.risk_score_calculator import RiskScoreCalculator
from concomplyai.risk_engine.scenario_simulator import (
    ScenarioConfig,
    ScenarioSimulator,
)
from concomplyai.vendor_risk.vendor_dashboard import VendorDashboard
from concomplyai.vendor_risk.vendor_profile import (
    ComplianceRecord,
    VendorCertification,
    VendorProfile,
)

# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    timestamp: datetime


class ViolationCounts(BaseModel):
    """Violation breakdown by severity for report generation."""
    CRITICAL: int = 0
    HIGH: int = 0
    MEDIUM: int = 0
    LOW: int = 0


class ReportRequest(BaseModel):
    """Request body for generating a compliance report."""
    title: str = Field(default="Compliance Report", description="Report title.")
    period_start: datetime = Field(..., description="Start of the reporting period (UTC).")
    period_end: datetime = Field(..., description="End of the reporting period (UTC).")
    violations: ViolationCounts = Field(
        default_factory=ViolationCounts,
        description="Violation counts by severity.",
    )


class RiskFactorInput(BaseModel):
    """Input schema matching RiskFactor fields."""
    factor_id: str
    name: str
    category: Literal["REGULATORY", "OPERATIONAL", "FINANCIAL", "SAFETY", "VENDOR"]
    weight: float = Field(ge=0.0, le=1.0)
    current_value: float = Field(ge=0.0, le=100.0)
    description: str


class RiskCalculateRequest(BaseModel):
    """Request body for risk score calculation."""
    entity_id: str = Field(..., description="Entity identifier.")
    entity_type: Literal["PROJECT", "CONTRACTOR", "VENDOR", "SITE"] = Field(
        ..., description="Entity classification."
    )
    factors: list[RiskFactorInput] = Field(
        ..., min_length=1, description="Risk factors to aggregate."
    )


class ScenarioConfigInput(BaseModel):
    """Input schema for a scenario configuration."""
    name: str
    description: str
    factor_adjustments: dict[str, float] = Field(
        ..., description="factor_id -> new value mapping."
    )


class ScenarioSimulateRequest(BaseModel):
    """Request body for running a what-if simulation."""
    base_entity_id: str = Field(..., description="Entity whose profile to simulate against.")
    base_entity_type: Literal["PROJECT", "CONTRACTOR", "VENDOR", "SITE"] = Field(
        ..., description="Entity classification."
    )
    base_factors: list[RiskFactorInput] = Field(
        ..., min_length=1, description="Baseline risk factors."
    )
    scenario: ScenarioConfigInput = Field(..., description="Scenario to simulate.")


class CertificationInput(BaseModel):
    """Input schema for a vendor certification."""
    cert_id: str
    name: str
    issuing_body: str
    issue_date: datetime
    expiry_date: datetime
    is_valid: bool = True


class ComplianceRecordInput(BaseModel):
    """Input schema for a compliance check record."""
    record_id: str
    check_date: datetime
    passed: bool
    category: str
    details: str


class VendorAddRequest(BaseModel):
    """Request body for adding a vendor."""
    vendor_id: str
    company_name: str
    industry: str
    certifications: list[CertificationInput] = Field(default_factory=list)
    compliance_history: list[ComplianceRecordInput] = Field(default_factory=list)
    contact_email: str


# ---------------------------------------------------------------------------
# Service singletons (lazily initialised on first use)
# ---------------------------------------------------------------------------

_event_bus: EventBus | None = None
_reporting_agent: ReportingAgent | None = None
_monitoring_agent: MonitoringAgent | None = None
_risk_calculator: RiskScoreCalculator | None = None
_scenario_simulator: ScenarioSimulator | None = None
_vendor_dashboard: VendorDashboard | None = None
_decision_logger: DecisionLogger | None = None
_audit_exporter: AuditExporter | None = None


def _get_event_bus() -> EventBus:
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus


def _get_reporting_agent() -> ReportingAgent:
    global _reporting_agent
    if _reporting_agent is None:
        _reporting_agent = ReportingAgent(_get_event_bus())
    return _reporting_agent


def _get_monitoring_agent() -> MonitoringAgent:
    global _monitoring_agent
    if _monitoring_agent is None:
        _monitoring_agent = MonitoringAgent(_get_event_bus())
    return _monitoring_agent


def _get_risk_calculator() -> RiskScoreCalculator:
    global _risk_calculator
    if _risk_calculator is None:
        _risk_calculator = RiskScoreCalculator(_get_event_bus())
    return _risk_calculator


def _get_scenario_simulator() -> ScenarioSimulator:
    global _scenario_simulator
    if _scenario_simulator is None:
        _scenario_simulator = ScenarioSimulator(_get_risk_calculator())
    return _scenario_simulator


def _get_vendor_dashboard() -> VendorDashboard:
    global _vendor_dashboard
    if _vendor_dashboard is None:
        _vendor_dashboard = VendorDashboard(_get_event_bus())
    return _vendor_dashboard


def _get_decision_logger() -> DecisionLogger:
    global _decision_logger
    if _decision_logger is None:
        _decision_logger = DecisionLogger(_get_event_bus())
    return _decision_logger


def _get_audit_exporter() -> AuditExporter:
    global _audit_exporter
    if _audit_exporter is None:
        _audit_exporter = AuditExporter(_get_decision_logger())
    return _audit_exporter


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Return service health status."""
    return HealthResponse(
        status="healthy",
        version=__version__,
        timestamp=datetime.now(timezone.utc),
    )


# -- Compliance --------------------------------------------------------------


@router.post("/compliance/report")
async def generate_compliance_report(body: ReportRequest) -> dict[str, Any]:
    """Generate a compliance report from violation data."""
    agent = _get_reporting_agent()
    event = ComplianceEvent(
        event_type="compliance.report_request",
        source="api",
        payload={
            "title": body.title,
            "period_start": body.period_start.isoformat(),
            "period_end": body.period_end.isoformat(),
            "violations": body.violations.model_dump(),
        },
    )
    report = agent.generate_report(event)
    return report.model_dump(mode="json")


@router.get("/compliance/score")
async def get_compliance_score() -> dict[str, Any]:
    """Return current compliance monitoring metrics."""
    agent = _get_monitoring_agent()
    metrics = agent.get_metrics()
    return metrics.model_dump(mode="json")


# -- Risk --------------------------------------------------------------------


@router.post("/risk/calculate")
async def calculate_risk_score(body: RiskCalculateRequest) -> dict[str, Any]:
    """Calculate a risk profile from a set of risk factors."""
    calculator = _get_risk_calculator()
    factors = [
        RiskFactor(
            factor_id=f.factor_id,
            name=f.name,
            category=f.category,
            weight=f.weight,
            current_value=f.current_value,
            description=f.description,
        )
        for f in body.factors
    ]
    profile = calculator.calculate_profile(
        entity_id=body.entity_id,
        entity_type=body.entity_type,
        factors=factors,
    )
    return profile.model_dump(mode="json")


@router.post("/risk/simulate")
async def simulate_risk_scenario(body: ScenarioSimulateRequest) -> dict[str, Any]:
    """Run a what-if simulation against a baseline risk profile."""
    calculator = _get_risk_calculator()
    simulator = _get_scenario_simulator()

    factors = [
        RiskFactor(
            factor_id=f.factor_id,
            name=f.name,
            category=f.category,
            weight=f.weight,
            current_value=f.current_value,
            description=f.description,
        )
        for f in body.base_factors
    ]
    base_profile = calculator.calculate_profile(
        entity_id=body.base_entity_id,
        entity_type=body.base_entity_type,
        factors=factors,
    )
    scenario = ScenarioConfig(
        name=body.scenario.name,
        description=body.scenario.description,
        factor_adjustments=body.scenario.factor_adjustments,
    )
    result = simulator.simulate(base_profile, scenario)
    return result.model_dump(mode="json")


# -- Vendor ------------------------------------------------------------------


@router.get("/vendor/exposure")
async def get_vendor_exposure() -> dict[str, Any]:
    """Return the aggregate vendor exposure summary."""
    dashboard = _get_vendor_dashboard()
    summary = dashboard.get_exposure_summary()
    return summary.model_dump(mode="json")


@router.post("/vendor/add")
async def add_vendor(body: VendorAddRequest) -> dict[str, str]:
    """Register a new vendor and compute its risk score."""
    dashboard = _get_vendor_dashboard()
    certs = [
        VendorCertification(
            cert_id=c.cert_id,
            name=c.name,
            issuing_body=c.issuing_body,
            issue_date=c.issue_date,
            expiry_date=c.expiry_date,
            is_valid=c.is_valid,
        )
        for c in body.certifications
    ]
    records = [
        ComplianceRecord(
            record_id=r.record_id,
            check_date=r.check_date,
            passed=r.passed,
            category=r.category,
            details=r.details,
        )
        for r in body.compliance_history
    ]
    profile = VendorProfile(
        vendor_id=body.vendor_id,
        company_name=body.company_name,
        industry=body.industry,
        certifications=certs,
        compliance_history=records,
        contact_email=body.contact_email,
    )
    dashboard.add_vendor(profile)
    return {"status": "added", "vendor_id": body.vendor_id}


@router.get("/vendor/{vendor_id}")
async def get_vendor_report(vendor_id: str) -> dict[str, Any]:
    """Return the detailed risk report for a single vendor."""
    dashboard = _get_vendor_dashboard()
    report = dashboard.get_vendor_report(vendor_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Vendor not found")
    return report.model_dump(mode="json")


# -- Audit -------------------------------------------------------------------


@router.get("/audit/decisions")
async def list_audit_decisions(
    agent_name: Optional[str] = Query(default=None, description="Filter by agent name."),
    limit: int = Query(default=100, ge=1, le=10000, description="Max results."),
) -> list[dict[str, Any]]:
    """List audit decision log entries."""
    decision_logger = _get_decision_logger()
    entries = decision_logger.get_decisions(agent_name=agent_name, limit=limit)
    return [e.model_dump(mode="json") for e in entries]


@router.get("/audit/summary")
async def get_audit_summary(
    agent_name: Optional[str] = Query(default=None, description="Filter by agent name."),
) -> dict[str, Any]:
    """Return aggregate audit statistics."""
    exporter = _get_audit_exporter()
    summary = exporter.export_summary(agent_name=agent_name)
    return summary.model_dump(mode="json")


@router.get("/audit/export")
async def export_audit_log(
    agent_name: Optional[str] = Query(default=None, description="Filter by agent name."),
    limit: int = Query(default=1000, ge=1, le=10_000_000, description="Max records."),
) -> Any:
    """Export the full audit log as JSON."""
    exporter = _get_audit_exporter()
    raw = exporter.export_json(agent_name=agent_name, limit=limit)
    return json.loads(raw)
