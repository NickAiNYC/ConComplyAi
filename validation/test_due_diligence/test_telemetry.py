"""
Tests for Core Telemetry Module - Cost Tracking
"""
import pytest
import os
from pathlib import Path
from datetime import datetime

from packages.core.telemetry import (
    calculate_llm_cost,
    track_agent_cost,
    get_cost_summary,
    validate_cost_target,
    MODEL_PRICING
)


class TestCostCalculation:
    """Test cost calculation functions"""
    
    def test_calculate_cost_claude_haiku(self):
        """Verify Claude 3 Haiku cost calculation"""
        input_tokens = 1000
        output_tokens = 500
        
        expected_cost = (1000 * 0.00000025) + (500 * 0.00000125)
        actual_cost = calculate_llm_cost("claude-3-haiku", input_tokens, output_tokens)
        
        assert actual_cost == expected_cost
        assert actual_cost == 0.000875
    
    def test_meets_cost_target(self):
        """Test that Claude Haiku stays under $0.007/doc target"""
        # Typical COI validation: 1000 input + 300 output tokens
        cost = calculate_llm_cost("claude-3-haiku", 1000, 300)
        
        assert cost < 0.007, f"Cost {cost} exceeds $0.007 target"
        assert cost == 0.000625  # Expected cost


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
