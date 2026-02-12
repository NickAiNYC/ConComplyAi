"""Tests for concomplyai.audit (decision_logger, explainability_engine, audit_exporter).

Covers decision logging with SHA-256 hashes, retrieval by ID,
explainability explanations with confidence assessment, and JSON/summary
export functionality.
"""

import json
import re

import pytest
from pydantic import ValidationError

from concomplyai.core.event_bus import EventBus
from concomplyai.audit.decision_logger import DecisionLogger
from concomplyai.audit.explainability_engine import ExplainabilityEngine
from concomplyai.audit.audit_exporter import AuditExporter


SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class TestDecisionLogger:
    """Tests for the DecisionLogger."""

    @pytest.fixture
    def bus(self):
        return EventBus()

    @pytest.fixture
    def logger(self, bus):
        return DecisionLogger(bus)

    def test_log_decision_creates_entry_with_hash(self, logger):
        """Logging a decision should return an entry with a SHA-256 hash."""
        entry = logger.log_decision(
            agent_name="GuardAgent",
            decision="PASS",
            reasoning="All documents validated.",
            confidence=0.95,
            input_data={"doc_id": "DOC-001"},
        )

        assert entry.agent_name == "GuardAgent"
        assert entry.decision == "PASS"
        assert entry.confidence == 0.95
        assert SHA256_PATTERN.match(entry.entry_hash)

    def test_get_decisions_returns_logged_entries(self, logger):
        """get_decisions should return previously logged entries."""
        logger.log_decision(
            agent_name="ScoutAgent",
            decision="FAIL",
            reasoning="Missing permit.",
            confidence=0.8,
            input_data={"permit_id": "P-001"},
        )
        logger.log_decision(
            agent_name="GuardAgent",
            decision="PASS",
            reasoning="Documents OK.",
            confidence=0.9,
            input_data={"doc_id": "D-002"},
        )

        all_decisions = logger.get_decisions()
        assert len(all_decisions) == 2

        scout_decisions = logger.get_decisions(agent_name="ScoutAgent")
        assert len(scout_decisions) == 1
        assert scout_decisions[0].agent_name == "ScoutAgent"

    def test_get_decision_by_id(self, logger):
        """get_decision_by_id should return the exact matching entry."""
        entry = logger.log_decision(
            agent_name="WatchmanAgent",
            decision="PENDING_HUMAN_REVIEW",
            reasoning="Ambiguous site condition.",
            confidence=0.5,
            input_data={"site_id": "S-001"},
        )

        found = logger.get_decision_by_id(entry.decision_id)
        assert found is not None
        assert found.decision_id == entry.decision_id
        assert found.entry_hash == entry.entry_hash

    def test_get_decision_by_id_not_found(self, logger):
        """Non-existent decision ID should return None."""
        assert logger.get_decision_by_id("nonexistent-id") is None

    def test_entry_is_frozen(self, logger):
        """DecisionLogEntry should be immutable (frozen)."""
        entry = logger.log_decision(
            agent_name="TestAgent",
            decision="PASS",
            reasoning="OK",
            confidence=0.9,
            input_data={},
        )
        with pytest.raises(ValidationError):
            entry.decision = "FAIL"


class TestExplainabilityEngine:
    """Tests for the ExplainabilityEngine."""

    @pytest.fixture
    def engine(self):
        return ExplainabilityEngine()

    @pytest.fixture
    def sample_entry(self):
        bus = EventBus()
        dl = DecisionLogger(bus)
        return dl.log_decision(
            agent_name="GuardAgent",
            decision="PASS",
            reasoning="All safety checks cleared.",
            confidence=0.92,
            input_data={"check_type": "safety"},
        )

    def test_explain_decision_produces_explanation(self, engine, sample_entry):
        """explain_decision should return a populated DecisionExplanation."""
        explanation = engine.explain_decision(sample_entry)

        assert explanation.decision_id == sample_entry.decision_id
        assert explanation.agent_name == "GuardAgent"
        assert "PASS" in explanation.plain_language_summary
        assert len(explanation.key_factors) > 0

    def test_confidence_assessment_high(self, engine):
        """Confidence >= 0.8 should be assessed as HIGH CONFIDENCE."""
        bus = EventBus()
        dl = DecisionLogger(bus)
        entry = dl.log_decision(
            agent_name="Agent",
            decision="PASS",
            reasoning="Confident.",
            confidence=0.85,
            input_data={},
        )
        explanation = engine.explain_decision(entry)
        assert explanation.confidence_assessment == "HIGH CONFIDENCE"

    def test_confidence_assessment_moderate(self, engine):
        """Confidence >= 0.5 and < 0.8 should be MODERATE CONFIDENCE."""
        bus = EventBus()
        dl = DecisionLogger(bus)
        entry = dl.log_decision(
            agent_name="Agent",
            decision="PASS",
            reasoning="Somewhat sure.",
            confidence=0.6,
            input_data={},
        )
        explanation = engine.explain_decision(entry)
        assert explanation.confidence_assessment == "MODERATE CONFIDENCE"

    def test_confidence_assessment_low(self, engine):
        """Confidence < 0.5 should be LOW CONFIDENCE."""
        bus = EventBus()
        dl = DecisionLogger(bus)
        entry = dl.log_decision(
            agent_name="Agent",
            decision="PENDING_HUMAN_REVIEW",
            reasoning="Uncertain.",
            confidence=0.3,
            input_data={},
        )
        explanation = engine.explain_decision(entry)
        assert explanation.confidence_assessment == "LOW CONFIDENCE"


class TestAuditExporter:
    """Tests for the AuditExporter."""

    @pytest.fixture
    def bus(self):
        return EventBus()

    @pytest.fixture
    def decision_logger(self, bus):
        return DecisionLogger(bus)

    @pytest.fixture
    def exporter(self, decision_logger):
        return AuditExporter(decision_logger)

    def _log_sample_decisions(self, decision_logger):
        """Log a few sample decisions for export tests."""
        decision_logger.log_decision(
            agent_name="GuardAgent",
            decision="PASS",
            reasoning="OK",
            confidence=0.9,
            input_data={"id": "1"},
        )
        decision_logger.log_decision(
            agent_name="ScoutAgent",
            decision="FAIL",
            reasoning="Missing docs.",
            confidence=0.7,
            input_data={"id": "2"},
        )
        decision_logger.log_decision(
            agent_name="GuardAgent",
            decision="PASS",
            reasoning="All clear.",
            confidence=0.95,
            input_data={"id": "3"},
        )

    def test_export_json_produces_valid_json(self, exporter, decision_logger):
        """export_json should return a parseable JSON string."""
        self._log_sample_decisions(decision_logger)
        raw = exporter.export_json()
        data = json.loads(raw)
        assert isinstance(data, list)
        assert len(data) == 3
        assert all("decision_id" in record for record in data)

    def test_export_summary_correct_counts(self, exporter, decision_logger):
        """export_summary should count decisions per agent correctly."""
        self._log_sample_decisions(decision_logger)
        summary = exporter.export_summary()

        assert summary.total_decisions == 3
        assert summary.decisions_by_agent["GuardAgent"] == 2
        assert summary.decisions_by_agent["ScoutAgent"] == 1
        assert 0 < summary.average_confidence <= 1.0
        assert summary.date_range_start is not None
        assert summary.date_range_end is not None

    def test_export_summary_hash_integrity(self, exporter, decision_logger):
        """Summary hash must be a valid 64-char hex SHA-256."""
        self._log_sample_decisions(decision_logger)
        summary = exporter.export_summary()
        assert SHA256_PATTERN.match(summary.summary_hash)

    def test_export_summary_empty(self, exporter):
        """Summary with no decisions should have zero counts."""
        summary = exporter.export_summary()
        assert summary.total_decisions == 0
        assert summary.average_confidence == 0.0
