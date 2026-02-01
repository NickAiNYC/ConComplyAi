"""Vision Agent - OSHA-focused visual compliance analysis"""
from typing import List, Dict, Any
from datetime import datetime
from core.models import Violation, RiskLevel, AgentOutput, ConstructionState
from core.config import calculate_token_cost, mock_vision_result


def analyze_visual_compliance(state: ConstructionState) -> dict:
    """
    Specialized OSHA-focused vision analysis agent
    Focuses on fall protection, PPE, scaffolding, and structural safety
    Returns dict of state updates for LangGraph
    """
    try:
        # Call deterministic mock vision API with OSHA focus
        vision_response = mock_vision_result(state.site_id)
        
        # Parse violations with OSHA-specific categorization
        violations = []
        for v_data in vision_response["violations"]:
            # Add OSHA-specific metadata
            violation_dict = dict(v_data)
            violation_dict["agent_source"] = "vision_agent"
            violations.append(Violation(**violation_dict))
        
        # Calculate cost
        input_tokens = vision_response["input_tokens"]
        output_tokens = vision_response["output_tokens"]
        cost = calculate_token_cost(input_tokens, output_tokens)
        
        # MANDATORY: Print token cost
        print(f"[VISION_AGENT] TOKEN_COST_USD: ${cost:.6f} (in={input_tokens}, out={output_tokens})")
        
        # Log agent output with OSHA-specific insights
        agent_output = AgentOutput(
            agent_name="vision_agent",
            status="success",
            tokens_used=input_tokens + output_tokens,
            usd_cost=cost,
            timestamp=datetime.now(),
            data={
                "violations_found": len(violations),
                "osha_categories": list(set(v.category for v in violations)),
                "confidence_avg": sum(v.confidence for v in violations) / len(violations) if violations else 0.0,
                "focus_areas": ["fall_protection", "ppe", "scaffolding", "structural_safety"]
            }
        )
        
        agent_outputs = state.agent_outputs.copy()
        agent_outputs.append(agent_output)
        
        # Return dict of state updates for LangGraph
        return {
            "violations": violations,
            "total_tokens": state.total_tokens + (input_tokens + output_tokens),
            "total_cost": state.total_cost + cost,
            "agent_outputs": agent_outputs,
        }
        
    except Exception as e:
        errors = state.agent_errors.copy()
        errors.append(f"vision_agent failed: {str(e)}")
        
        agent_output = AgentOutput(
            agent_name="vision_agent",
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
