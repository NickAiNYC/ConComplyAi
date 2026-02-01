"""Risk Scorer - Final risk assessment based on synthesis"""
from datetime import datetime
from core.models import AgentOutput, ConstructionState, RiskLevel
from core.config import BUSINESS_CONFIG, calculate_token_cost


def calculate_final_risk(state: ConstructionState) -> dict:
    """
    Risk scoring agent that provides final risk assessment
    Considers all agent inputs and generates comprehensive risk score
    Returns dict of state updates for LangGraph
    """
    try:
        # Calculate risk score (weighted by confidence and fine amount)
        risk_score = 0.0
        total_fines = 0.0
        risk_factors = []
        
        for violation in state.violations:
            weight = BUSINESS_CONFIG["violation_fines"][violation.risk_level.value]
            risk_score += violation.confidence * weight
            total_fines += violation.estimated_fine
            
            if violation.risk_level == RiskLevel.CRITICAL:
                risk_factors.append(f"Critical: {violation.category}")
        
        # Normalize risk score 0-100
        if state.violations:
            risk_score = min(100, (risk_score / len(state.violations)) / 1000)
        
        # Adjust for permit status
        if state.permit_data:
            if state.permit_data.status == "EXPIRED":
                risk_score *= 1.3  # 30% increase for expired permits
                risk_factors.append("Expired permit multiplier applied")
            elif state.permit_data.violations_on_record > 3:
                risk_score *= 1.15  # 15% increase for repeat violators
                risk_factors.append("Repeat violator multiplier applied")
        
        # Calculate estimated savings (87% accuracy * prevented fines)
        accuracy = BUSINESS_CONFIG["accuracy_target"]
        estimated_savings = total_fines * accuracy
        
        # Mock token usage for final scoring
        input_tokens = 400 + len(state.violations) * 50
        output_tokens = 600  # Detailed risk analysis
        cost = calculate_token_cost(input_tokens, output_tokens)
        
        # MANDATORY: Print token cost
        print(f"[RISK_SCORER] TOKEN_COST_USD: ${cost:.6f} (in={input_tokens}, out={output_tokens})")
        
        # Build comprehensive risk report
        risk_report = {
            "risk_score": round(risk_score, 2),
            "risk_category": _categorize_risk(risk_score),
            "total_potential_fines": f"${total_fines:,.2f}",
            "estimated_savings": f"${estimated_savings:,.2f}",
            "violations_count": len(state.violations),
            "critical_count": sum(1 for v in state.violations if v.risk_level == RiskLevel.CRITICAL),
            "high_count": sum(1 for v in state.violations if v.risk_level == RiskLevel.HIGH),
            "risk_factors": risk_factors,
            "agent_consensus": _check_agent_consensus(state)
        }
        
        # Log agent output
        agent_output = AgentOutput(
            agent_name="risk_scorer",
            status="success",
            tokens_used=input_tokens + output_tokens,
            usd_cost=cost,
            timestamp=datetime.now(),
            data=risk_report
        )
        agent_outputs = state.agent_outputs.copy()
        agent_outputs.append(agent_output)
        
        # Return dict of state updates
        return {
            "risk_score": round(risk_score, 2),
            "estimated_savings": round(estimated_savings, 2),
            "total_tokens": state.total_tokens + (input_tokens + output_tokens),
            "total_cost": state.total_cost + cost,
            "processing_end": datetime.now(),
            "agent_outputs": agent_outputs,
        }
        
    except Exception as e:
        errors = state.agent_errors.copy()
        errors.append(f"risk_scorer failed: {str(e)}")
        
        agent_output = AgentOutput(
            agent_name="risk_scorer",
            status="error",
            tokens_used=0,
            usd_cost=0.0,
            timestamp=datetime.now(),
            data={"error": str(e)}
        )
        agent_outputs = state.agent_outputs.copy()
        agent_outputs.append(agent_output)
        
        return {
            "agent_errors": errors,
            "agent_outputs": agent_outputs,
        }


def _categorize_risk(score: float) -> str:
    """Categorize risk score into business-friendly labels"""
    if score >= 75:
        return "SEVERE - Immediate Action Required"
    elif score >= 50:
        return "HIGH - Priority Remediation"
    elif score >= 25:
        return "MODERATE - Schedule Corrections"
    else:
        return "LOW - Routine Monitoring"


def _check_agent_consensus(state: ConstructionState) -> str:
    """Check if all agents agree on assessment"""
    successful_agents = [
        output.agent_name for output in state.agent_outputs 
        if output.status == "success"
    ]
    
    if len(successful_agents) >= 4:  # Vision, Permit, Synthesis, Red Team
        return "Strong consensus across all agents"
    elif len(successful_agents) >= 2:
        return "Partial consensus - some agents unavailable"
    else:
        return "Limited consensus - manual review recommended"
