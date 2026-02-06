"""
Feasibility Agent - Task 4: Predictive Risk & Profitability Drain

Calculates feasibility scores and projected profitability drain from insurance gaps.
Uses 'Skeptical' veteran logic for conservative risk assessment.

Maintains $0.007/doc cost efficiency target.
"""
from typing import Dict, Any, List
from datetime import datetime

from packages.core import (
    ScopeSignal,
    FeasibilityScore,
    AgencyRequirement,
    DecisionProof,
    AgentHandshake
)


class FeasibilityAgent:
    """
    Agent responsible for assessing bid feasibility and calculating
    profitability drain from insurance compliance gaps.
    
    Uses 'Skeptical' veteran logic - assumes worst-case scenarios
    for insurance costs and agency enforcement.
    """
    
    AGENT_ID = "FeasibilityAgent-v2.0"
    
    # Insurance premium estimates (annual, per $1M coverage)
    # Based on 'Skeptical' veteran estimates - conservative/high-end
    BASE_PREMIUM_RATES = {
        "General Liability": 12000,  # $12k per $1M
        "Professional Liability": 8000,
        "Pollution Liability": 15000,
        "Auto Liability": 5000,
        "Workers Comp": 8000,  # Per $100k payroll
        "Umbrella": 3000
    }
    
    # Endorsement costs (one-time or per project)
    ENDORSEMENT_COSTS = {
        "Additional Insured - Primary & Non-Contributory": 500,
        "Additional Insured - Broad Form": 500,
        "Additional Insured": 300,
        "Waiver of Subrogation": 750,
        "Per Project Aggregate": 1200,
        "Notice of Cancellation - 30 days": 0,  # Usually included
        "Notice of Cancellation - 60 days": 0,
        "Pollution Liability for Renovation Projects": 8000,
        "Professional Liability (if design services)": 5000,
        "Lead-Based Paint Coverage": 3500,
        "Highway Traffic Liability": 2000
    }
    
    # Agency strictness multipliers (Skeptical veteran wisdom)
    AGENCY_RISK_MULTIPLIERS = {
        AgencyRequirement.SCA: 1.5,  # School Construction Authority - strictest
        AgencyRequirement.DDC: 1.3,  # DDC is tough but reasonable
        AgencyRequirement.HPD: 1.2,  # HPD is moderate
        AgencyRequirement.DOT: 1.4   # DOT has unique requirements
    }
    
    # Cost tracking
    TOKEN_COST_PER_1K = 0.002
    AVERAGE_TOKENS_PER_ASSESSMENT = 250
    
    def __init__(self):
        self.assessments_completed = 0
        self.total_cost = 0.0
    
    def assess_feasibility(
        self,
        signal: ScopeSignal,
        estimated_project_value: float,
        estimated_profit_margin: float = 0.15,  # 15% default
        from_agent: str = "OpportunityAgent"
    ) -> FeasibilityScore:
        """
        Assess bid feasibility and calculate profitability drain.
        
        Args:
            signal: The ScopeSignal opportunity
            estimated_project_value: Total project value in USD
            estimated_profit_margin: Expected profit margin (0.0-1.0)
            from_agent: Source agent for handshake tracking
            
        Returns:
            FeasibilityScore with profitability drain predictions
        """
        # Calculate insurance gaps cost
        premium_increase = self._calculate_premium_increase(signal)
        
        # Calculate agency risk multiplier
        risk_multiplier = self._calculate_risk_multiplier(signal.agency_requirements)
        
        # Apply skeptical veteran logic - multiply by risk
        adjusted_premium_increase = premium_increase * risk_multiplier
        
        # Calculate profitability drain
        estimated_profit = estimated_project_value * estimated_profit_margin
        profitability_drain = (adjusted_premium_increase / estimated_profit) * 100 if estimated_profit > 0 else 100.0
        
        # Calculate bid adjustment needed
        bid_adjustment = adjusted_premium_increase * 1.2  # Add 20% buffer
        
        # Calculate overall feasibility score
        overall_score = self._calculate_feasibility_score(
            signal,
            profitability_drain,
            risk_multiplier
        )
        
        # Determine recommendation
        recommendation = self._generate_recommendation(
            overall_score,
            profitability_drain,
            signal
        )
        
        # Build reasoning chain
        reasoning = self._build_reasoning(
            signal,
            premium_increase,
            risk_multiplier,
            profitability_drain,
            overall_score
        )
        
        # Create agent handshake for governance audit
        handshake = AgentHandshake(
            from_agent=from_agent,
            to_agent=self.AGENT_ID,
            handshake_timestamp=datetime.now(),
            transition_reason=f"Feasibility assessment for {signal.project_name}",
            data_passed={
                "signal_id": signal.signal_id,
                "project_value": estimated_project_value,
                "profit_margin": estimated_profit_margin,
                "insurance_gaps": signal.insurance_gaps,
                "required_endorsements": signal.missing_endorsements
            },
            validation_status="handoff_validated"
        )
        
        # Create decision proof
        decision_proof = DecisionProof(
            agent_id=self.AGENT_ID,
            timestamp=datetime.now(),
            logic_citation="Skeptical Veteran Risk Assessment Framework 2027",
            confidence_score=0.85,
            decision_type="validation",
            input_data={
                "signal_id": signal.signal_id,
                "project_value": estimated_project_value,
                "profit_margin": estimated_profit_margin,
                "agencies": [a.value for a in signal.agency_requirements]
            },
            output_action=f"Feasibility: {recommendation}, Score: {overall_score:.1f}",
            reasoning_chain=reasoning,
            agent_handshake=handshake
        )
        
        # Track cost
        tokens = self.AVERAGE_TOKENS_PER_ASSESSMENT
        cost = (tokens / 1000) * self.TOKEN_COST_PER_1K
        self._track_cost(cost)
        
        # Build risk factors breakdown
        risk_factors = {
            "base_premium_increase": premium_increase,
            "agency_strictness_multiplier": risk_multiplier,
            "gap_count": len(signal.insurance_gaps) + len(signal.missing_endorsements),
            "project_complexity": self._assess_complexity(signal)
        }
        
        self.assessments_completed += 1
        
        return FeasibilityScore(
            signal_id=signal.signal_id,
            project_id=signal.project_id,
            overall_score=overall_score,
            confidence=0.85,
            current_insurance_gaps=signal.insurance_gaps,
            required_endorsements=signal.missing_endorsements,
            projected_premium_increase=adjusted_premium_increase,
            projected_profitability_drain=profitability_drain,
            estimated_bid_adjustment=bid_adjustment,
            risk_factors=risk_factors,
            calculation_tokens=tokens,
            calculation_cost=cost,
            recommendation=recommendation,
            reasoning=reasoning
        )
    
    def _calculate_premium_increase(self, signal: ScopeSignal) -> float:
        """
        Calculate estimated premium increase from missing endorsements.
        Uses skeptical veteran estimates (conservative/high).
        """
        total_cost = 0.0
        
        # Add endorsement costs
        for endorsement in signal.missing_endorsements:
            cost = self.ENDORSEMENT_COSTS.get(endorsement, 1000)  # $1k default if unknown
            total_cost += cost
        
        # Add coverage gap costs (estimate based on gap type)
        for gap in signal.insurance_gaps:
            if "liability" in gap.lower():
                total_cost += 8000
            elif "pollution" in gap.lower():
                total_cost += 15000
            elif "professional" in gap.lower():
                total_cost += 5000
            else:
                total_cost += 3000  # Generic gap estimate
        
        return total_cost
    
    def _calculate_risk_multiplier(self, agencies: List[AgencyRequirement]) -> float:
        """
        Calculate composite risk multiplier based on agencies involved.
        Skeptical veteran logic: Use maximum multiplier among all agencies.
        """
        if not agencies:
            return 1.0
        
        # Use max multiplier (most strict agency wins)
        multipliers = [self.AGENCY_RISK_MULTIPLIERS.get(a, 1.0) for a in agencies]
        return max(multipliers)
    
    def _assess_complexity(self, signal: ScopeSignal) -> float:
        """Assess project complexity (0-1 scale)."""
        complexity = 0.0
        
        # More agencies = more complex
        complexity += len(signal.agency_requirements) * 0.2
        
        # More gaps = more complex
        gap_count = len(signal.insurance_gaps) + len(signal.missing_endorsements)
        complexity += min(gap_count * 0.1, 0.5)
        
        # Cap at 1.0
        return min(complexity, 1.0)
    
    def _calculate_feasibility_score(
        self,
        signal: ScopeSignal,
        profitability_drain: float,
        risk_multiplier: float
    ) -> float:
        """
        Calculate overall feasibility score (0-100).
        Lower score = less feasible to bid.
        """
        base_score = 100.0
        
        # Deduct for profitability drain
        if profitability_drain > 50:
            base_score -= 40  # Severe drain
        elif profitability_drain > 30:
            base_score -= 25  # High drain
        elif profitability_drain > 15:
            base_score -= 15  # Moderate drain
        else:
            base_score -= 5   # Manageable drain
        
        # Deduct for agency complexity
        base_score -= (risk_multiplier - 1.0) * 20
        
        # Deduct for gap count
        gap_count = len(signal.insurance_gaps) + len(signal.missing_endorsements)
        base_score -= min(gap_count * 3, 20)
        
        # Bonus if monitoring already active (we have data)
        if signal.has_active_monitoring:
            base_score += 10
        
        return max(min(base_score, 100.0), 0.0)
    
    def _generate_recommendation(
        self,
        score: float,
        drain: float,
        signal: ScopeSignal
    ) -> str:
        """Generate bid recommendation."""
        if score >= 70 and drain < 20:
            return "bid_with_caution"
        elif score >= 50:
            return "bid_after_compliance"
        else:
            return "do_not_bid"
    
    def _build_reasoning(
        self,
        signal: ScopeSignal,
        premium_increase: float,
        risk_multiplier: float,
        drain: float,
        score: float
    ) -> List[str]:
        """Build reasoning chain for transparency."""
        reasoning = [
            f"Analyzed {len(signal.insurance_gaps)} insurance gaps",
            f"Identified {len(signal.missing_endorsements)} missing endorsements",
            f"Base premium increase: ${premium_increase:,.2f}",
            f"Agency risk multiplier: {risk_multiplier}x (Skeptical veteran adjustment)",
            f"Adjusted premium increase: ${premium_increase * risk_multiplier:,.2f}",
            f"Profitability drain: {drain:.1f}% of profit margin",
            f"Overall feasibility score: {score:.1f}/100",
            f"Project monitoring status: {'Active' if signal.has_active_monitoring else 'Not active'}"
        ]
        
        # Add agency-specific notes
        for agency in signal.agency_requirements:
            reasoning.append(f"Agency {agency.value} strictness factor: {self.AGENCY_RISK_MULTIPLIERS.get(agency, 1.0)}x")
        
        return reasoning
    
    def _track_cost(self, cost: float):
        """Track cost for efficiency monitoring."""
        self.total_cost += cost
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get agent statistics."""
        avg_cost = self.total_cost / self.assessments_completed if self.assessments_completed > 0 else 0
        
        return {
            "agent_id": self.AGENT_ID,
            "assessments_completed": self.assessments_completed,
            "total_cost_usd": self.total_cost,
            "avg_cost_per_assessment": avg_cost,
            "meets_efficiency_target": avg_cost <= 0.007,
            "target_cost": 0.007
        }
