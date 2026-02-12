"""What-if scenario simulation against existing risk profiles.

``ScenarioSimulator`` applies hypothetical factor adjustments to an
existing ``RiskProfile`` and produces ``SimulationResult`` objects that
quantify the projected impact—enabling decision-makers to evaluate
mitigation strategies before committing resources.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from concomplyai.risk_engine.risk_model import (
    RiskFactor,
    RiskProfile,
    compute_risk_level,
)
from concomplyai.risk_engine.risk_score_calculator import RiskScoreCalculator

logger = logging.getLogger(__name__)


class ScenarioConfig(BaseModel):
    """Definition of a single what-if scenario."""

    model_config = ConfigDict(frozen=True)

    scenario_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for this scenario.",
    )
    name: str = Field(
        ...,
        description="Short human-readable name for the scenario.",
    )
    description: str = Field(
        ...,
        description="Detailed explanation of the scenario assumptions.",
    )
    factor_adjustments: dict[str, float] = Field(
        ...,
        description=(
            "Mapping of factor_id to the new current_value to assume. "
            "Only factors present in this mapping are modified; all "
            "others retain their original values."
        ),
    )


class SimulationResult(BaseModel):
    """Outcome of running a scenario simulation."""

    model_config = ConfigDict(frozen=True)

    scenario_id: str = Field(
        ...,
        description="Identifier of the evaluated scenario.",
    )
    scenario_name: str = Field(
        ...,
        description="Name of the evaluated scenario.",
    )
    original_score: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Risk score before the scenario adjustments.",
    )
    projected_score: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Risk score after applying the scenario adjustments.",
    )
    score_delta: float = Field(
        ...,
        description="Difference between projected and original scores.",
    )
    risk_level_change: str = Field(
        ...,
        description="Textual description of the risk-level transition (e.g. 'HIGH -> MEDIUM').",
    )
    impacted_factors: list[str] = Field(
        ...,
        description="Factor IDs whose values were modified by the scenario.",
    )
    simulated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of the simulation run.",
    )


class ScenarioSimulator:
    """Runs what-if simulations by adjusting factor values on an existing profile.

    The simulator never mutates the original ``RiskProfile``; instead it
    constructs new ``RiskFactor`` instances with adjusted values and
    delegates scoring to a ``RiskScoreCalculator``.
    """

    def __init__(self, calculator: RiskScoreCalculator) -> None:
        self._calculator = calculator

    def simulate(
        self,
        base_profile: RiskProfile,
        scenario: ScenarioConfig,
    ) -> SimulationResult:
        """Run a single what-if scenario against *base_profile*.

        Each factor whose ``factor_id`` appears in
        ``scenario.factor_adjustments`` has its ``current_value``
        replaced with the mapped value (clamped to 0-100).  The
        resulting factors are scored and compared to the original.

        Args:
            base_profile: The current risk profile to use as baseline.
            scenario: Configuration describing the adjustments.

        Returns:
            A ``SimulationResult`` capturing the projected impact.
        """
        adjusted_factors: list[RiskFactor] = []
        impacted_factors: list[str] = []

        for factor in base_profile.factors:
            if factor.factor_id in scenario.factor_adjustments:
                new_value = max(
                    0.0,
                    min(100.0, scenario.factor_adjustments[factor.factor_id]),
                )
                adjusted_factors.append(
                    RiskFactor(
                        factor_id=factor.factor_id,
                        name=factor.name,
                        category=factor.category,
                        weight=factor.weight,
                        current_value=new_value,
                        description=factor.description,
                    )
                )
                impacted_factors.append(factor.factor_id)
            else:
                adjusted_factors.append(factor)

        projected_score = self._calculator.calculate_score(adjusted_factors)
        original_score = base_profile.overall_score
        score_delta = round(projected_score - original_score, 2)

        original_level = base_profile.risk_level
        projected_level = compute_risk_level(projected_score)
        risk_level_change = f"{original_level} -> {projected_level}"

        result = SimulationResult(
            scenario_id=scenario.scenario_id,
            scenario_name=scenario.name,
            original_score=original_score,
            projected_score=projected_score,
            score_delta=score_delta,
            risk_level_change=risk_level_change,
            impacted_factors=impacted_factors,
        )

        logger.info(
            '{"action":"simulation_complete","scenario":"%s","delta":%.2f,"change":"%s"}',
            scenario.name,
            score_delta,
            risk_level_change,
        )
        return result

    def compare_scenarios(
        self,
        base_profile: RiskProfile,
        scenarios: list[ScenarioConfig],
    ) -> list[SimulationResult]:
        """Run multiple scenarios and return results for comparison.

        Results are returned in the same order as the input *scenarios*
        list to allow straightforward positional correlation.

        Args:
            base_profile: The baseline risk profile.
            scenarios: One or more scenario configurations to evaluate.

        Returns:
            List of ``SimulationResult`` objects, one per scenario.
        """
        return [self.simulate(base_profile, sc) for sc in scenarios]
