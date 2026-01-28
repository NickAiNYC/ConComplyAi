"""Report Generator Agent - Executive PDF with cost analysis"""
from datetime import datetime
from models import AgentOutput, ConstructionState, RiskLevel
from config import BUSINESS_CONFIG, calculate_token_cost


def generate_report(state: ConstructionState) -> ConstructionState:
    """
    Generate executive report with risk scoring and ROI calculation
    Prints TOKEN_COST_USD after every call
    """
    try:
        # Calculate risk score (weighted by confidence and fine amount)
        risk_score = 0.0
        total_fines = 0.0
        
        for violation in state.violations:
            weight = BUSINESS_CONFIG["violation_fines"][violation.risk_level.value]
            risk_score += violation.confidence * weight
            total_fines += violation.estimated_fine
        
        # Normalize risk score 0-100
        if state.violations:
            risk_score = min(100, (risk_score / len(state.violations)) / 1000)
        
        # Calculate estimated savings (87% accuracy * prevented fines)
        accuracy = BUSINESS_CONFIG["accuracy_target"]
        estimated_savings = total_fines * accuracy
        
        # Mock token usage for report generation
        input_tokens = 500 + len(state.violations) * 50
        output_tokens = 800  # Executive summary
        cost = calculate_token_cost(input_tokens, output_tokens)
        
        # MANDATORY: Print token cost
        print(f"[REPORT] TOKEN_COST_USD: ${cost:.6f} (in={input_tokens}, out={output_tokens})")
        
        # Update state
        state.risk_score = round(risk_score, 2)
        state.estimated_savings = round(estimated_savings, 2)
        state.total_tokens += (input_tokens + output_tokens)
        state.total_cost += cost
        state.processing_end = datetime.now()
        
        # Build report data structure
        report_data = {
            "executive_summary": {
                "site_id": state.site_id,
                "risk_score": state.risk_score,
                "violations_detected": len(state.violations),
                "critical_violations": sum(1 for v in state.violations if v.risk_level == RiskLevel.CRITICAL),
                "estimated_savings": f"${estimated_savings:,.2f}",
                "processing_time": _calculate_processing_time(state),
                "total_cost": f"${state.total_cost:.4f}"
            },
            "violations": [
                {
                    "id": v.violation_id,
                    "category": v.category,
                    "description": v.description,
                    "risk_level": v.risk_level.value,
                    "confidence": f"{v.confidence*100:.1f}%",
                    "fine": f"${v.estimated_fine:,}",
                    "location": v.location
                }
                for v in state.violations
            ],
            "cost_breakdown": {
                "total_tokens": state.total_tokens,
                "total_cost_usd": round(state.total_cost, 4),
                "cost_per_violation": round(state.total_cost / max(len(state.violations), 1), 4),
                "under_budget": state.total_cost <= BUSINESS_CONFIG["cost_per_site_budget"]
            },
            "permit_info": {
                "permit_number": state.permit_data.permit_number if state.permit_data else "N/A",
                "status": state.permit_data.status if state.permit_data else "API Unavailable",
                "violations_on_record": state.permit_data.violations_on_record if state.permit_data else 0
            }
        }
        
        # Log agent output
        state.agent_outputs.append(AgentOutput(
            agent_name="report_generator",
            status="success",
            tokens_used=input_tokens + output_tokens,
            usd_cost=cost,
            timestamp=datetime.now(),
            data=report_data
        ))
        
    except Exception as e:
        state.agent_errors.append(f"report_generator failed: {str(e)}")
        state.agent_outputs.append(AgentOutput(
            agent_name="report_generator",
            status="error",
            tokens_used=0,
            usd_cost=0.0,
            timestamp=datetime.now(),
            data={"error": str(e)}
        ))
    
    return state


def _calculate_processing_time(state: ConstructionState) -> str:
    """Calculate human-readable processing time"""
    if state.processing_start and state.processing_end:
        delta = state.processing_end - state.processing_start
        seconds = delta.total_seconds()
        if seconds < 60:
            return f"{seconds:.1f}s"
        return f"{seconds/60:.1f}m"
    return "N/A"
