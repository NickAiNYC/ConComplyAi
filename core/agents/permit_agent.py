"""Permit Agent - NYC Building Codes specialist"""
from datetime import datetime
from core.models import AgentOutput, ConstructionState, PermitData
from core.config import MockNYCApiClient, BUSINESS_CONFIG
from pybreaker import CircuitBreakerError


def analyze_permit_compliance(state: ConstructionState) -> dict:
    """
    Specialized NYC Building Code compliance agent
    Focuses on permit status, code violations, and regulatory requirements
    Returns dict of state updates for LangGraph
    """
    try:
        # Attempt to fetch permit data with circuit breaker
        permit_data = None
        api_client = MockNYCApiClient()
        permit_violations = []
        
        for attempt in range(BUSINESS_CONFIG["retry_limits"]["max_attempts"]):
            try:
                permit_data = api_client.get_permit_violations(state.site_id)
                
                # Add permit-based violation insights
                if permit_data and permit_data.violations_on_record > 0:
                    # Track historical permit violations
                    permit_violations.append({
                        "source": "permit_records",
                        "count": permit_data.violations_on_record,
                        "status": permit_data.status
                    })
                break
            except (ConnectionError, CircuitBreakerError) as e:
                if attempt == BUSINESS_CONFIG["retry_limits"]["max_attempts"] - 1:
                    error_msg = f"NYC API failed after {attempt+1} attempts: {str(e)}"
                    errors = state.agent_errors.copy()
                    errors.append(error_msg)
                else:
                    import time
                    backoff = min(
                        BUSINESS_CONFIG["retry_limits"]["backoff_base"] ** attempt,
                        BUSINESS_CONFIG["retry_limits"]["max_backoff"]
                    )
                    time.sleep(backoff)
        
        # Mock token usage for permit analysis (smaller than vision)
        input_tokens = 300  # Permit data + prompt
        output_tokens = 200  # Analysis summary
        
        # Calculate mock cost (permit agent uses cheaper models)
        cost = input_tokens * 0.0000015 + output_tokens * 0.000006  # GPT-3.5 pricing
        
        print(f"[PERMIT_AGENT] TOKEN_COST_USD: ${cost:.6f} (in={input_tokens}, out={output_tokens})")
        
        # Log agent output
        agent_output = AgentOutput(
            agent_name="permit_agent",
            status="success",
            tokens_used=input_tokens + output_tokens,
            usd_cost=cost,
            timestamp=datetime.now(),
            data={
                "permit_status": permit_data.status if permit_data else "unavailable",
                "violations_on_record": permit_data.violations_on_record if permit_data else 0,
                "permit_valid": permit_data.status == "ACTIVE" if permit_data else False,
                "api_calls": api_client.call_count,
                "focus_areas": ["nyc_building_code", "permit_compliance", "zoning"]
            }
        )
        
        agent_outputs = state.agent_outputs.copy()
        agent_outputs.append(agent_output)
        
        # Return dict of state updates
        return {
            "permit_data": permit_data,
            "total_tokens": state.total_tokens + (input_tokens + output_tokens),
            "total_cost": state.total_cost + cost,
            "agent_outputs": agent_outputs,
        }
        
    except Exception as e:
        errors = state.agent_errors.copy()
        errors.append(f"permit_agent failed: {str(e)}")
        
        agent_output = AgentOutput(
            agent_name="permit_agent",
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
