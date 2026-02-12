"""Tests for concomplyai.reg_monitor (change_listener, regulation_diff_engine, rule_updater).

Covers source registration, update detection, diff computation with
severity classification, and rule impact assessment with recommendations.
"""

import re

import pytest

from concomplyai.core.event_bus import EventBus
from concomplyai.reg_monitor.change_listener import RegulatoryChangeListener
from concomplyai.reg_monitor.regulation_diff_engine import RegulationDiffEngine
from concomplyai.reg_monitor.rule_updater import RuleUpdater


SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class TestChangeListener:
    """Tests for the RegulatoryChangeListener."""

    @pytest.fixture
    def listener(self):
        return RegulatoryChangeListener()

    def test_register_source_and_get_tracked(self, listener):
        """Registering a source should make it appear in tracked sources."""
        listener.register_source(
            source_id="nyc-ll97",
            name="NYC Local Law 97",
            current_version="1.0",
            url="https://example.com/ll97",
        )
        sources = listener.get_tracked_sources()
        assert len(sources) == 1
        assert sources[0].source_id == "nyc-ll97"
        assert sources[0].current_version == "1.0"

    def test_check_for_updates_with_version_change(self, listener):
        """A version change should return a RegulatoryUpdate record."""
        listener.register_source(
            source_id="ll97",
            name="LL97",
            current_version="1.0",
            url="https://example.com/ll97",
        )

        update = listener.check_for_updates(
            source_id="ll97",
            new_version="2.0",
            new_text="Updated regulation text with new requirements.",
        )

        assert update is not None
        assert update.old_version == "1.0"
        assert update.new_version == "2.0"
        assert update.source_id == "ll97"
        assert "LL97" in update.changes_summary

    def test_check_for_updates_no_change_returns_none(self, listener):
        """Same version should return None (no update detected)."""
        listener.register_source(
            source_id="ll97",
            name="LL97",
            current_version="1.0",
            url="https://example.com/ll97",
        )

        result = listener.check_for_updates(
            source_id="ll97",
            new_version="1.0",
            new_text="Same text.",
        )
        assert result is None

    def test_check_unregistered_source_raises(self, listener):
        """Checking an unregistered source should raise KeyError."""
        with pytest.raises(KeyError, match="not registered"):
            listener.check_for_updates("unknown", "1.0", "text")


class TestDiffEngine:
    """Tests for the RegulationDiffEngine."""

    @pytest.fixture
    def engine(self):
        return RegulationDiffEngine()

    def test_compute_diff_minor_changes(self, engine):
        """Small changes relative to total lines should be MINOR."""
        old_text = "\n".join([f"Line {i}" for i in range(100)])
        # Change 1 line out of 100 -> ~1% change -> MINOR
        lines = [f"Line {i}" for i in range(100)]
        lines[0] = "Modified Line 0"
        new_text = "\n".join(lines)

        diff = engine.compute_diff(old_text, new_text)
        assert diff.change_severity == "MINOR"
        assert len(diff.added_lines) >= 1
        assert len(diff.removed_lines) >= 1

    def test_compute_diff_major_changes(self, engine):
        """Large proportion of changed lines should be MAJOR or BREAKING."""
        old_text = "\n".join([f"Old line {i}" for i in range(10)])
        new_text = "\n".join([f"New line {i}" for i in range(10)])

        diff = engine.compute_diff(old_text, new_text)
        assert diff.change_severity in ("MAJOR", "BREAKING")

    def test_compute_diff_identical_text(self, engine):
        """Identical texts should produce MINOR severity with no changes."""
        text = "Section 1: Requirements\nSection 2: Standards"
        diff = engine.compute_diff(text, text)

        assert diff.change_severity == "MINOR"
        assert len(diff.added_lines) == 0
        assert len(diff.removed_lines) == 0


class TestRuleUpdater:
    """Tests for the RuleUpdater."""

    @pytest.fixture
    def bus(self):
        return EventBus()

    @pytest.fixture
    def updater(self, bus):
        return RuleUpdater(bus)

    @pytest.fixture
    def engine(self):
        return RegulationDiffEngine()

    def test_evaluate_impact(self, updater, engine):
        """evaluate_impact should produce an ImpactAssessment with risk level."""
        diff = engine.compute_diff(
            "Old regulation text here",
            "New regulation text with major updates here",
        )
        assessment = updater.evaluate_impact(diff, ["RULE-001", "RULE-002"])

        assert assessment.diff_id == diff.diff_id
        assert assessment.impacted_rules == ["RULE-001", "RULE-002"]
        assert assessment.risk_level in ("LOW", "MEDIUM", "HIGH", "CRITICAL")

    def test_generate_recommendations(self, updater, engine):
        """generate_recommendations should return one recommendation per rule."""
        diff = engine.compute_diff("Old text", "Completely new text here")
        assessment = updater.evaluate_impact(diff, ["R-001", "R-002", "R-003"])

        recs = updater.generate_recommendations(assessment)
        assert len(recs) == 3
        assert all(r.rule_id in ("R-001", "R-002", "R-003") for r in recs)
        assert all(r.priority >= 1 and r.priority <= 5 for r in recs)
        assert all(r.deadline_days >= 0 for r in recs)

    def test_assessment_hash_integrity(self, updater, engine):
        """Assessment hash must be a valid 64-char hex SHA-256 string."""
        diff = engine.compute_diff("Old", "New")
        assessment = updater.evaluate_impact(diff, ["RULE-X"])
        assert SHA256_PATTERN.match(assessment.assessment_hash)
