"""Violation Detector Agent - Mock GPT-4o Vision with deterministic output"""
from typing import List
import random
from datetime import datetime
from models import Violation, RiskLevel, AgentOutput, ConstructionState
from config import (
    MockNYCApiClient, 
    calculate_token_cost, 
    get_risk_level,
    BUSINESS_CONFIG
)


def detect_violations(state: ConstructionState) -> ConstructionState:
    """
    Mock GPT-4o Vision API - Deterministic violation detection
    Demonstrates: Service abstraction, token tracking, error isolation
    """
    # Seed for deterministic output in demos
    random.seed(hash(state.site_id) % 2**32)
    
    try:
        # Mock vision analysis - deterministic based on site_id
        violations = _mock_vision_analysis(state.site_id)
        
        # Mock token usage (realistic for image + prompt)
        input_tokens = 1500  # Image tokens + prompt
        output_tokens = len(violations) * 80  # ~80 tokens per violation
        cost = calculate_token_cost(input_tokens, output_tokens)
        
        # Attempt to fetch permit data with circuit breaker
        permit_data = None
        api_client = MockNYCApiClient()
        
        for attempt in range(BUSINESS_CONFIG["retry_limits"]["max_attempts"]):
            try:
                permit_data = api_client.get_permit_violations(state.site_id)
                break
            except ConnectionError as e:
                if attempt == BUSINESS_CONFIG["retry_limits"]["max_attempts"] - 1:
                    # Circuit breaker open - use fallback
                    state.agent_errors.append(f"NYC API failed after {attempt+1} attempts: {str(e)}")
                    # Continue with vision-only data
                else:
                    # Exponential backoff
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


def _mock_vision_analysis(site_id: str) -> List[Violation]:
    """
    Deterministic mock of GPT-4o Vision analysis
    Production signal: Prompt includes cost-awareness instruction
    """
    # Deterministic output based on site_id hash
    seed_val = hash(site_id) % 100
    
    violations = []
    
    # Hudson Yards style site - multiple high-value violations
    if seed_val < 30:  # 30% have critical violations
        violations.append(Violation(
            violation_id=f"{site_id}-V001",
            category="Structural Safety",
            description="Unsecured scaffolding on 45+ story building, immediate collapse risk",
            confidence=0.94,
            risk_level=RiskLevel.CRITICAL,
            estimated_fine=75000,
            location="Exterior South Face, Floor 45"
        ))
    
    if seed_val < 60:  # 60% have high-risk violations
        violations.append(Violation(
            violation_id=f"{site_id}-V002",
            category="Fall Protection",
            description="Missing guardrails at roof edge, OSHA 1926.501 violation",
            confidence=0.88,
            risk_level=RiskLevel.HIGH,
            estimated_fine=25000,
            location="Roof Perimeter, North Section"
        ))
    
    if seed_val < 85:  # 85% have medium violations
        violations.append(Violation(
            violation_id=f"{site_id}-V003",
            category="Site Management",
            description="Debris accumulation blocking fire exit route",
            confidence=0.65,
            risk_level=RiskLevel.MEDIUM,
            estimated_fine=5000,
            location="Ground Level, Exit C"
        ))
    
    return violations
