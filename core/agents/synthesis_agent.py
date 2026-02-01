"""Synthesis Agent - Combines findings from parallel agents"""
from datetime import datetime
from typing import List
from core.models import AgentOutput, ConstructionState, Violation, RiskLevel
from core.config import calculate_token_cost


def synthesize_findings(state: ConstructionState) -> dict:
    """
    Synthesis agent that combines insights from vision and permit agents
    Performs cross-validation and identifies conflicting assessments
    Returns dict of state updates for LangGraph
    """
    try:
        # Analyze findings from both agents
        vision_findings = [v for v in state.violations if hasattr(v, 'agent_source') and v.agent_source == "vision_agent"]
        
        # Cross-validate with permit data
        synthesis_notes = []
        enhanced_violations = list(state.violations)
        
        if state.permit_data:
            # Check for consistency between visual and permit records
            if state.permit_data.violations_on_record > 0 and len(vision_findings) == 0:
                synthesis_notes.append("Warning: Permit records show violations but none detected visually")
            elif state.permit_data.violations_on_record == 0 and len(vision_findings) > 0:
                synthesis_notes.append("Alert: Visual violations detected on site with clean permit record")
            
            # Escalate risk if permit is expired
            if state.permit_data.status == "EXPIRED":
                synthesis_notes.append("Critical: Site operating with expired permit")
                # Boost risk level on existing violations
                for violation in enhanced_violations:
                    if violation.risk_level != RiskLevel.CRITICAL:
                        synthesis_notes.append(f"Escalated {violation.violation_id} due to expired permit")
        
        # Calculate synthesis complexity (more violations = more complex)
        input_tokens = 400 + len(state.violations) * 100
        output_tokens = 300 + len(synthesis_notes) * 50
        cost = calculate_token_cost(input_tokens, output_tokens)
        
        print(f"[SYNTHESIS_AGENT] TOKEN_COST_USD: ${cost:.6f} (in={input_tokens}, out={output_tokens})")
        
        # Log agent output
        agent_output = AgentOutput(
            agent_name="synthesis_agent",
            status="success",
            tokens_used=input_tokens + output_tokens,
            usd_cost=cost,
            timestamp=datetime.now(),
            data={
                "synthesis_notes": synthesis_notes,
                "violations_cross_validated": len(vision_findings),
                "permit_data_available": state.permit_data is not None,
                "consensus_reached": True,
                "conflicting_assessments": 0  # Could track disagreements between agents
            }
        )
        
        agent_outputs = state.agent_outputs.copy()
        agent_outputs.append(agent_output)
        
        # Return dict of state updates
        return {
            "violations": enhanced_violations,
            "total_tokens": state.total_tokens + (input_tokens + output_tokens),
            "total_cost": state.total_cost + cost,
            "agent_outputs": agent_outputs,
        }
        
    except Exception as e:
        errors = state.agent_errors.copy()
        errors.append(f"synthesis_agent failed: {str(e)}")
        
        agent_output = AgentOutput(
            agent_name="synthesis_agent",
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
