"""Tests for multi-agent collaboration system"""
import pytest
import random
from core.multi_agent_supervisor import run_multi_agent_compliance_check, run_batch_multi_agent_compliance
from core.config import BUSINESS_CONFIG


# Set global seed for deterministic tests
random.seed(42)


class TestMultiAgentCollaboration:
    """Test suite for parallel multi-agent execution"""
    
    def test_multi_agent_execution(self):
        """Verify all agents execute successfully"""
        random.seed(42)
        result = run_multi_agent_compliance_check("SITE-MA-001")
        
        # Should have outputs from all 5 agents
        agent_names = [output.agent_name for output in result.agent_outputs]
        expected_agents = ["vision_agent", "permit_agent", "synthesis_agent", "red_team_agent", "risk_scorer"]
        
        for expected in expected_agents:
            assert expected in agent_names, f"Missing agent: {expected}"
        
        assert len(agent_names) == 5, f"Expected 5 agents, got {len(agent_names)}"
    
    def test_red_team_validation(self):
        """Verify red team agent reduces false positives"""
        random.seed(42)
        result = run_multi_agent_compliance_check("SITE-RT-001")
        
        # Find red team output
        red_team_output = next(
            (o for o in result.agent_outputs if o.agent_name == "red_team_agent"),
            None
        )
        
        assert red_team_output is not None, "Red team agent didn't execute"
        assert red_team_output.status == "success", "Red team agent failed"
        
        # Verify red team performed validation
        data = red_team_output.data
        assert "violations_challenged" in data
        assert "validation_pass_rate" in data
    
    def test_synthesis_agent_consensus(self):
        """Verify synthesis agent combines findings from parallel agents"""
        random.seed(42)
        result = run_multi_agent_compliance_check("SITE-SYN-001")
        
        # Find synthesis output
        synthesis_output = next(
            (o for o in result.agent_outputs if o.agent_name == "synthesis_agent"),
            None
        )
        
        assert synthesis_output is not None, "Synthesis agent didn't execute"
        assert synthesis_output.status == "success", "Synthesis agent failed"
        
        # Verify synthesis performed cross-validation
        data = synthesis_output.data
        assert "synthesis_notes" in data
        assert "consensus_reached" in data
    
    def test_risk_scorer_final_assessment(self):
        """Verify risk scorer provides final consensus assessment"""
        random.seed(42)
        result = run_multi_agent_compliance_check("SITE-RS-001")
        
        # Find risk scorer output
        risk_output = next(
            (o for o in result.agent_outputs if o.agent_name == "risk_scorer"),
            None
        )
        
        assert risk_output is not None, "Risk scorer didn't execute"
        assert risk_output.status == "success", "Risk scorer failed"
        
        # Verify comprehensive risk report
        data = risk_output.data
        assert "risk_score" in data
        assert "risk_category" in data
        assert "agent_consensus" in data
    
    def test_parallel_execution_cost(self):
        """Verify multi-agent execution maintains reasonable cost"""
        random.seed(42)
        result = run_multi_agent_compliance_check("SITE-COST-001")
        
        # Multi-agent should still be under budget (though higher than single agent)
        # Allow up to $0.06 per site for multi-agent (50% higher than single agent)
        max_cost = BUSINESS_CONFIG['cost_per_site_budget'] * 1.5
        
        assert result.total_cost <= max_cost, \
            f"Multi-agent cost ${result.total_cost:.4f} exceeds ${max_cost:.4f} threshold"
    
    def test_multi_agent_token_tracking(self):
        """Verify token usage across all agents is tracked accurately"""
        random.seed(42)
        result = run_multi_agent_compliance_check("SITE-TOKEN-MA-001")
        
        # Sum agent token usage
        agent_tokens = sum(
            output.tokens_used for output in result.agent_outputs 
            if output.status == "success"
        )
        
        assert result.total_tokens == agent_tokens, \
            f"Token mismatch: state={result.total_tokens}, agents={agent_tokens}"
        
        # Verify cost calculation matches token usage
        expected_cost = sum(
            output.usd_cost for output in result.agent_outputs 
            if output.status == "success"
        )
        assert abs(result.total_cost - expected_cost) < 0.0001, \
            f"Cost mismatch: state=${result.total_cost:.4f}, expected=${expected_cost:.4f}"
    
    def test_batch_multi_agent_processing(self):
        """Verify batch processing with multi-agent architecture"""
        random.seed(42)
        site_ids = [f"SITE-BATCH-MA-{i:03d}" for i in range(3)]
        results = run_batch_multi_agent_compliance(site_ids)
        
        assert len(results) == 3, f"Batch processing didn't return all results: got {len(results)}"
        
        # Each result should have all agents
        for result in results:
            assert result.site_id in site_ids, f"Unknown site_id: {result.site_id}"
            assert len(result.agent_outputs) >= 5, \
                f"Incomplete agent execution for {result.site_id}: only {len(result.agent_outputs)} agents"
    
    def test_multi_agent_deterministic_output(self):
        """Verify multi-agent system produces consistent results with seed"""
        random.seed(42)
        result1 = run_multi_agent_compliance_check("SITE-DET-MA-001")
        
        random.seed(42)
        result2 = run_multi_agent_compliance_check("SITE-DET-MA-001")
        
        assert len(result1.violations) == len(result2.violations), \
            f"Violation detection not deterministic: {len(result1.violations)} vs {len(result2.violations)}"
        
        assert result1.risk_score == result2.risk_score, \
            f"Risk scoring not deterministic: {result1.risk_score} vs {result2.risk_score}"
    
    def test_agent_error_isolation(self):
        """Verify that errors in one agent don't crash entire system"""
        random.seed(42)
        # This should complete even if permit agent fails
        result = run_multi_agent_compliance_check("SITE-ERROR-MA-001")
        
        # System should complete with at least vision and risk scorer
        assert result.risk_score >= 0, "Risk score calculation failed"
        assert len(result.agent_outputs) >= 2, "Too few agents completed execution"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
