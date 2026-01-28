"""Config and Mock API clients - Production-style service abstraction"""
import random
import time
from typing import Optional
from models import PermitData, RiskLevel
from datetime import datetime, timedelta


class MockNYCApiClient:
    """Mock NYC DOB/HPD API with realistic latency and 23% failure rate"""
    
    def __init__(self, failure_rate: float = 0.23):
        self.failure_rate = failure_rate
        self.call_count = 0
        
    def get_permit_violations(self, site_id: str) -> Optional[PermitData]:
        """Simulate API call with latency and failures"""
        self.call_count += 1
        
        # Simulate network latency 50-200ms
        time.sleep(random.uniform(0.05, 0.2))
        
        # 23% failure rate
        if random.random() < self.failure_rate:
            raise ConnectionError(f"NYC API unavailable for site {site_id}")
        
        # Mock successful response
        return PermitData(
            site_id=site_id,
            permit_number=f"BLD-2024-{random.randint(10000, 99999)}",
            status=random.choice(["ACTIVE", "EXPIRED", "PENDING"]),
            expiration_date=datetime.now() + timedelta(days=random.randint(-30, 180)),
            violations_on_record=random.randint(0, 5)
        )


# Business Rules - Production Thresholds
BUSINESS_CONFIG = {
    "risk_thresholds": {
        RiskLevel.CRITICAL: 0.9,
        RiskLevel.HIGH: 0.7,
        RiskLevel.MEDIUM: 0.4,
        RiskLevel.LOW: 0.0
    },
    "cost_per_site_budget": 0.04,  # $0.04 per site max
    "max_tokens_per_site": 4000,
    "retry_limits": {
        "max_attempts": 3,
        "backoff_base": 2,  # Exponential: 2^attempt seconds
        "max_backoff": 10
    },
    "openai_pricing": {
        "gpt4o_vision_input": 0.0000025,  # $2.50 per 1M tokens
        "gpt4o_vision_output": 0.00001,   # $10 per 1M tokens
    },
    "violation_fines": {
        "CRITICAL": 75000,  # Structural failure
        "HIGH": 25000,      # Safety hazard
        "MEDIUM": 5000,     # Code violation
        "LOW": 500          # Minor infraction
    },
    "accuracy_target": 0.87,  # 87% detection accuracy
    "expected_savings_per_violation": 1_490_000,  # $1.49M per critical violation caught
    "processing_sla": 7200  # 2 hours for 1000 sites
}


def calculate_token_cost(input_tokens: int, output_tokens: int) -> float:
    """Calculate OpenAI cost for GPT-4o Vision"""
    pricing = BUSINESS_CONFIG["openai_pricing"]
    return (input_tokens * pricing["gpt4o_vision_input"] + 
            output_tokens * pricing["gpt4o_vision_output"])


def get_risk_level(confidence: float) -> RiskLevel:
    """Map confidence to business risk level"""
    thresholds = BUSINESS_CONFIG["risk_thresholds"]
    if confidence >= thresholds[RiskLevel.CRITICAL]:
        return RiskLevel.CRITICAL
    elif confidence >= thresholds[RiskLevel.HIGH]:
        return RiskLevel.HIGH
    elif confidence >= thresholds[RiskLevel.MEDIUM]:
        return RiskLevel.MEDIUM
    return RiskLevel.LOW
