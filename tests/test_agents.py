"""Tests for concomplyai.agents (remediation, reporting, monitoring).

Covers RemediationAgent severity mapping, ReportingAgent report
generation and scoring, and MonitoringAgent metrics and alerting.
"""

import re

import pytest
from pydantic import ValidationError

from concomplyai.core.event_bus import ComplianceEvent, EventBus
from concomplyai.agents.remediation_agent import RemediationAgent, RemediationAction
from concomplyai.agents.reporting_agent import ReportingAgent, ComplianceReport
from concomplyai.agents.monitoring_agent import MonitoringAgent, MonitoringAlert


SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def _violation_event(severity: str, violation_id: str = "V-001") -> ComplianceEvent:
    """Helper to create a compliance.violation event."""
    return ComplianceEvent(
        event_type="compliance.violation",
        source="test",
        payload={"violation_id": violation_id},
        severity=severity,
    )


class TestRemediationAgent:
    """Tests for the RemediationAgent."""

    @pytest.fixture
    def agent(self):
        bus = EventBus()
        return RemediationAgent(bus)

    def test_critical_event_escalate(self, agent):
        """CRITICAL severity should produce ESCALATE action."""
        event = _violation_event("CRITICAL")
        action = agent.handle_violation(event)
        assert action.action_type == "ESCALATE"
        assert action.priority == 1
        assert action.assigned_to == "compliance-lead"

    def test_high_event_manual_review(self, agent):
        """HIGH severity should produce MANUAL_REVIEW action."""
        event = _violation_event("HIGH")
        action = agent.handle_violation(event)
        assert action.action_type == "MANUAL_REVIEW"
        assert action.priority == 2
        assert action.assigned_to == "compliance-team"

    def test_medium_event_auto_fix(self, agent):
        """MEDIUM severity should produce AUTO_FIX action."""
        event = _violation_event("MEDIUM")
        action = agent.handle_violation(event)
        assert action.action_type == "AUTO_FIX"
        assert action.priority == 3
        assert action.assigned_to is None

    def test_low_event_notify(self, agent):
        """LOW severity should produce NOTIFY action."""
        event = _violation_event("LOW")
        action = agent.handle_violation(event)
        assert action.action_type == "NOTIFY"
        assert action.priority == 4
        assert action.assigned_to is None

    def test_decision_hash_is_sha256(self, agent):
        """Decision hash must be a 64-character hex SHA-256 string."""
        event = _violation_event("MEDIUM")
        action = agent.handle_violation(event)
        assert SHA256_PATTERN.match(action.decision_hash)

    def test_action_is_frozen(self, agent):
        """RemediationAction should be immutable (frozen)."""
        event = _violation_event("LOW")
        action = agent.handle_violation(event)
        with pytest.raises(ValidationError):
            action.action_type = "ESCALATE"


class TestReportingAgent:
    """Tests for the ReportingAgent."""

    @pytest.fixture
    def agent(self):
        bus = EventBus()
        return ReportingAgent(bus)

    def _report_event(self, violations=None):
        """Helper to create a compliance.report_request event."""
        if violations is None:
            violations = {"CRITICAL": 1, "HIGH": 2, "MEDIUM": 5, "LOW": 10}
        return ComplianceEvent(
            event_type="compliance.report_request",
            source="test",
            payload={
                "title": "Q1 Compliance Report",
                "period_start": "2025-01-01T00:00:00+00:00",
                "period_end": "2025-03-31T23:59:59+00:00",
                "violations": violations,
            },
        )

    def test_generate_report_from_violation_data(self, agent):
        """Report should be generated with correct violation counts."""
        event = self._report_event()
        report = agent.generate_report(event)

        assert report.title == "Q1 Compliance Report"
        assert report.critical_count == 1
        assert report.high_count == 2
        assert report.medium_count == 5
        assert report.low_count == 10
        assert report.total_violations == 18

    def test_compliance_score_calculation(self, agent):
        """Compliance score should decrease with more/severe violations."""
        # No violations -> perfect score
        event_clean = self._report_event(
            {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        )
        clean_report = agent.generate_report(event_clean)
        assert clean_report.compliance_score == 100.0

        # Many violations -> lower score
        event_bad = self._report_event(
            {"CRITICAL": 5, "HIGH": 3, "MEDIUM": 2, "LOW": 1}
        )
        bad_report = agent.generate_report(event_bad)
        assert bad_report.compliance_score < clean_report.compliance_score

    def test_report_hash_is_sha256(self, agent):
        """Report hash must be a 64-character hex SHA-256 string."""
        event = self._report_event()
        report = agent.generate_report(event)
        assert SHA256_PATTERN.match(report.report_hash)

    def test_report_is_frozen(self, agent):
        """ComplianceReport should be immutable (frozen)."""
        event = self._report_event()
        report = agent.generate_report(event)
        with pytest.raises(ValidationError):
            report.title = "Changed Title"


class TestMonitoringAgent:
    """Tests for the MonitoringAgent."""

    @pytest.fixture
    def bus(self):
        return EventBus()

    @pytest.fixture
    def agent(self, bus):
        return MonitoringAgent(bus)

    def test_process_event_increments_metrics(self, agent):
        """Processing an event should increment total_events count."""
        event = ComplianceEvent(
            event_type="compliance.violation",
            source="test",
            severity="MEDIUM",
        )
        agent.process_event(event)

        metrics = agent.get_metrics()
        assert metrics.total_events == 1

    def test_alert_generation_on_threshold(self, agent):
        """Exceeding the critical threshold should produce an alert."""
        for i in range(5):
            event = ComplianceEvent(
                event_type="compliance.violation",
                source="test",
                severity="CRITICAL",
            )
            result = agent.process_event(event)

        assert result is not None
        assert isinstance(result, MonitoringAlert)
        assert result.alert_type == "critical_threshold_exceeded"
        assert result.severity == "CRITICAL"

    def test_metrics_tracking_by_type_and_severity(self, agent):
        """Metrics should track counts by event type and severity."""
        agent.process_event(
            ComplianceEvent(
                event_type="compliance.violation",
                source="test",
                severity="HIGH",
            )
        )
        agent.process_event(
            ComplianceEvent(
                event_type="compliance.alert",
                source="test",
                severity="LOW",
            )
        )

        metrics = agent.get_metrics()
        assert metrics.events_by_type["compliance.violation"] == 1
        assert metrics.events_by_type["compliance.alert"] == 1
        assert metrics.events_by_severity["HIGH"] == 1
        assert metrics.events_by_severity["LOW"] == 1

    def test_non_critical_event_returns_none(self, agent):
        """Non-critical events should not generate alerts."""
        event = ComplianceEvent(
            event_type="compliance.violation",
            source="test",
            severity="LOW",
        )
        result = agent.process_event(event)
        assert result is None
