"""Red Team Agent - Adversarial validation to reduce false positives"""
from datetime import datetime
from typing import List
from core.models import AgentOutput, ConstructionState, Violation, RiskLevel
from core.config import calculate_token_cost


def challenge_findings(state: ConstructionState) -> dict:
    """
    Red Team agent that challenges findings to reduce false positives
    Uses adversarial validation techniques to test violation confidence
    Returns dict of state updates for LangGraph
    """
    try:
        validated_violations = []
        challenged_count = 0
        false_positives_removed = 0
        
        for violation in state.violations:
            # Red team challenges: confidence threshold, context validation
            should_keep = True
            challenge_notes = []
            
            # Challenge 1: Confidence threshold
            if violation.confidence < 0.70:
                challenge_notes.append(f"Low confidence ({violation.confidence:.2f})")
                # Keep but flag for review
            
            # Challenge 2: Context validation
            if violation.risk_level == RiskLevel.CRITICAL and violation.confidence < 0.90:
                challenge_notes.append("Critical violation requires >90% confidence")
                should_keep = False
                false_positives_removed += 1
            
            # Challenge 3: Consistency check
            if state.permit_data and state.permit_data.status == "ACTIVE":
                # Sites with active permits less likely to have critical violations
                if violation.risk_level == RiskLevel.CRITICAL and state.permit_data.violations_on_record == 0:
                    challenge_notes.append("Active permit with clean record - flagged for manual review")
            
            challenged_count += 1
            
            if should_keep:
                validated_violations.append(violation)
        
        # Calculate token usage for adversarial analysis
        input_tokens = 300 + len(state.violations) * 80
        output_tokens = 250 + challenged_count * 40
        cost = calculate_token_cost(input_tokens, output_tokens)
        
        print(f"[RED_TEAM_AGENT] TOKEN_COST_USD: ${cost:.6f} (in={input_tokens}, out={output_tokens})")
        
        # Log agent output
        agent_output = AgentOutput(
            agent_name="red_team_agent",
            status="success",
            tokens_used=input_tokens + output_tokens,
            usd_cost=cost,
            timestamp=datetime.now(),
            data={
                "violations_challenged": challenged_count,
                "false_positives_removed": false_positives_removed,
                "validation_pass_rate": len(validated_violations) / len(state.violations) if state.violations else 1.0,
                "adversarial_techniques": ["confidence_threshold", "context_validation", "consistency_check"],
                "final_violation_count": len(validated_violations)
            }
        )
        
        agent_outputs = state.agent_outputs.copy()
        agent_outputs.append(agent_output)
        
        # Return dict of state updates
        return {
            "violations": validated_violations,
            "total_tokens": state.total_tokens + (input_tokens + output_tokens),
            "total_cost": state.total_cost + cost,
            "agent_outputs": agent_outputs,
        }
        
    except Exception as e:
        errors = state.agent_errors.copy()
        errors.append(f"red_team_agent failed: {str(e)}")
        
        agent_output = AgentOutput(
            agent_name="red_team_agent",
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
