"""Tests for concomplyai.risk_engine (risk_model, risk_score_calculator, scenario_simulator).

Covers risk level boundaries, RiskFactor creation, weighted score
calculation, profile generation with hashes, trend tracking, and
scenario simulation.
"""

import re

import pytest

from concomplyai.core.event_bus import EventBus
from concomplyai.risk_engine.risk_model import (
    RiskFactor,
    compute_risk_level,
)
from concomplyai.risk_engine.risk_score_calculator import RiskScoreCalculator
from concomplyai.risk_engine.scenario_simulator import (
    ScenarioConfig,
    ScenarioSimulator,
)


SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def _make_factor(
    factor_id: str = "F1",
    weight: float = 1.0,
    current_value: float = 50.0,
    category: str = "REGULATORY",
) -> RiskFactor:
    """Helper to build a RiskFactor with sensible defaults."""
    return RiskFactor(
        factor_id=factor_id,
        name=f"Factor {factor_id}",
        category=category,
        weight=weight,
        current_value=current_value,
        description=f"Test factor {factor_id}",
    )


class TestRiskModel:
    """Tests for compute_risk_level and RiskFactor."""

    @pytest.mark.parametrize(
        "score, expected_level",
        [
            (0, "LOW"),
            (25, "LOW"),
            (26, "MEDIUM"),
            (50, "MEDIUM"),
            (51, "HIGH"),
            (75, "HIGH"),
            (76, "CRITICAL"),
            (100, "CRITICAL"),
        ],
    )
    def test_compute_risk_level_boundaries(self, score, expected_level):
        """Risk level should match documented thresholds."""
        assert compute_risk_level(score) == expected_level

    def test_compute_risk_level_out_of_range(self):
        """Scores outside 0-100 should raise ValueError."""
        with pytest.raises(ValueError):
            compute_risk_level(-1)
        with pytest.raises(ValueError):
            compute_risk_level(101)

    def test_risk_factor_creation(self):
        """RiskFactor should accept valid fields and be frozen."""
        factor = _make_factor()
        assert factor.factor_id == "F1"
        assert factor.weight == 1.0
        assert factor.current_value == 50.0
        assert factor.category == "REGULATORY"


class TestRiskScoreCalculator:
    """Tests for the RiskScoreCalculator."""

    @pytest.fixture
    def calculator(self):
        return RiskScoreCalculator()

    def test_calculate_score_single_factor(self, calculator):
        """Single factor: score should equal factor's current_value."""
        factor = _make_factor(weight=1.0, current_value=60.0)
        score = calculator.calculate_score([factor])
        assert score == 60.0

    def test_calculate_score_multiple_weighted_factors(self, calculator):
        """Weighted average across multiple factors should be computed correctly."""
        f1 = _make_factor(factor_id="F1", weight=0.6, current_value=80.0)
        f2 = _make_factor(factor_id="F2", weight=0.4, current_value=20.0)
        score = calculator.calculate_score([f1, f2])
        # (0.6*80 + 0.4*20) / (0.6+0.4) = (48 + 8) / 1.0 = 56.0
        assert score == 56.0

    def test_calculate_score_empty_factors(self, calculator):
        """Empty factor list should return 0.0."""
        assert calculator.calculate_score([]) == 0.0

    def test_calculate_profile_generates_hash(self, calculator):
        """calculate_profile must produce a profile with a valid SHA-256 hash."""
        factor = _make_factor(current_value=40.0)
        profile = calculator.calculate_profile(
            entity_id="PROJ-001",
            entity_type="PROJECT",
            factors=[factor],
        )
        assert SHA256_PATTERN.match(profile.profile_hash)
        assert profile.entity_id == "PROJ-001"
        assert profile.risk_level == compute_risk_level(profile.overall_score)

    def test_track_trend_direction_detection(self, calculator):
        """Trend should detect DEGRADING when scores increase significantly."""
        calculator.track_trend("E1", 20.0)
        calculator.track_trend("E1", 40.0)
        trend = calculator.track_trend("E1", 60.0)

        assert trend.entity_id == "E1"
        assert trend.trend_direction == "DEGRADING"
        assert trend.change_rate > 0

    def test_track_trend_improving(self, calculator):
        """Trend should detect IMPROVING when scores decrease significantly."""
        calculator.track_trend("E2", 80.0)
        calculator.track_trend("E2", 60.0)
        trend = calculator.track_trend("E2", 40.0)

        assert trend.trend_direction == "IMPROVING"
        assert trend.change_rate < 0

    def test_track_trend_stable(self, calculator):
        """Trend should be STABLE for small score changes."""
        calculator.track_trend("E3", 50.0)
        trend = calculator.track_trend("E3", 50.5)

        assert trend.trend_direction == "STABLE"


class TestScenarioSimulator:
    """Tests for the ScenarioSimulator."""

    @pytest.fixture
    def calculator(self):
        return RiskScoreCalculator()

    @pytest.fixture
    def simulator(self, calculator):
        return ScenarioSimulator(calculator)

    def _base_profile(self, calculator):
        """Build a baseline risk profile for simulation tests."""
        factors = [
            _make_factor(factor_id="F1", weight=0.5, current_value=60.0),
            _make_factor(factor_id="F2", weight=0.5, current_value=40.0),
        ]
        return calculator.calculate_profile(
            entity_id="PROJ-SIM",
            entity_type="PROJECT",
            factors=factors,
        )

    def test_simulate_produces_correct_delta(self, simulator, calculator):
        """Simulation should reflect the score change from factor adjustments."""
        profile = self._base_profile(calculator)

        scenario = ScenarioConfig(
            name="Reduce F1",
            description="Lower F1 to 20",
            factor_adjustments={"F1": 20.0},
        )

        result = simulator.simulate(profile, scenario)

        assert result.original_score == profile.overall_score
        assert result.projected_score != result.original_score
        assert result.score_delta == pytest.approx(
            result.projected_score - result.original_score, abs=0.01
        )
        assert "F1" in result.impacted_factors

    def test_compare_scenarios(self, simulator, calculator):
        """compare_scenarios should return one result per scenario."""
        profile = self._base_profile(calculator)

        scenarios = [
            ScenarioConfig(
                name="Improve F1",
                description="Lower F1",
                factor_adjustments={"F1": 10.0},
            ),
            ScenarioConfig(
                name="Worsen F2",
                description="Raise F2",
                factor_adjustments={"F2": 90.0},
            ),
        ]

        results = simulator.compare_scenarios(profile, scenarios)
        assert len(results) == 2
        assert results[0].scenario_name == "Improve F1"
        assert results[1].scenario_name == "Worsen F2"
