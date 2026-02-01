"""Violation Detector Agent - Deterministic mock with token cost logging"""
from typing import List
from datetime import datetime
from core.models import Violation, RiskLevel, AgentOutput, ConstructionState
from core.config import (
    MockNYCApiClient, 
    calculate_token_cost, 
    mock_vision_result,
    BUSINESS_CONFIG
)
from pybreaker import CircuitBreakerError


def detect_violations(state: ConstructionState) -> ConstructionState:
    """
    Deterministic violation detection using mock_vision_result
    Prints TOKEN_COST_USD after every call
    """
    try:
        # Call deterministic mock vision API
        vision_response = mock_vision_result(state.site_id)
        
        # Parse violations
        violations = []
        for v_data in vision_response["violations"]:
            violations.append(Violation(**v_data))
        
        # Calculate cost
        input_tokens = vision_response["input_tokens"]
        output_tokens = vision_response["output_tokens"]
        cost = calculate_token_cost(input_tokens, output_tokens)
        
        # MANDATORY: Print token cost
        print(f"[VISION] TOKEN_COST_USD: ${cost:.6f} (in={input_tokens}, out={output_tokens})")
        
        # Attempt to fetch permit data with circuit breaker
        permit_data = None
        api_client = MockNYCApiClient()
        
        for attempt in range(BUSINESS_CONFIG["retry_limits"]["max_attempts"]):
            try:
                permit_data = api_client.get_permit_violations(state.site_id)
                break
            except (ConnectionError, CircuitBreakerError) as e:
                if attempt == BUSINESS_CONFIG["retry_limits"]["max_attempts"] - 1:
                    state.agent_errors.append(f"NYC API failed after {attempt+1} attempts: {str(e)}")
                else:
                    import time
                    backoff = min(
                        BUSINESS_CONFIG["retry_limits"]["backoff_base"] ** attempt,
                        BUSINESS_CONFIG["retry_limits"]["max_backoff"]
                    )
                    time.sleep(backoff)
        
        # Update state
        state.violations = violations
        state.permit_data = permit_data
        state.total_tokens += (input_tokens + output_tokens)
        state.total_cost += cost
        
        # Log agent output
        state.agent_outputs.append(AgentOutput(
            agent_name="violation_detector",
            status="success",
            tokens_used=input_tokens + output_tokens,
            usd_cost=cost,
            timestamp=datetime.now(),
            data={
                "violations_found": len(violations),
                "permit_status": permit_data.status if permit_data else "unavailable",
                "api_calls": api_client.call_count
            }
        ))
        
    except Exception as e:
        state.agent_errors.append(f"violation_detector failed: {str(e)}")
        state.agent_outputs.append(AgentOutput(
            agent_name="violation_detector",
            status="error",
            tokens_used=0,
            usd_cost=0.0,
            timestamp=datetime.now(),
            data={"error": str(e)}
        ))
    
    return state
