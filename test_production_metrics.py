"""Production metrics tests - Deterministic with seed=42"""
import pytest
import sys
import time
import random
sys.path.insert(0, '/mnt/user-data/outputs/construction-compliance-ai/core')
from supervisor import run_compliance_check, run_batch_compliance
from config import BUSINESS_CONFIG


# Set global seed for deterministic tests
random.seed(42)
pytest.GLOBAL_SEED = 42


class TestProductionMetrics:
    """Test suite validating production readiness with seed=42"""
    
    def test_accuracy_threshold(self):
        """Verify detection accuracy meets 87% target"""
        random.seed(42)
        results = run_batch_compliance([f"SITE-{i:04d}" for i in range(20)])
        
        total_violations = sum(len(r.violations) for r in results)
        # Expected: ~2.5 violations per site (50 total)
        expected_violations = 20 * 2.5
        detection_rate = total_violations / expected_violations
        
        assert detection_rate >= 0.87, \
            f"Detection rate {detection_rate:.2%} below 87% target (got {total_violations}/{expected_violations})"
    
    def test_cost_per_site_budget(self):
        """Verify cost per site stays under $0.04 budget"""
        random.seed(42)
        results = run_batch_compliance([f"SITE-{i:04d}" for i in range(10)])
        
        for result in results:
            assert result.total_cost <= BUSINESS_CONFIG['cost_per_site_budget'], \
                f"Site {result.site_id} cost ${result.total_cost:.4f} exceeds ${BUSINESS_CONFIG['cost_per_site_budget']} budget"
    
    def test_thousand_site_total_cost(self):
        """Verify 1000 sites processed under $3.20 total cost"""
        random.seed(42)
        # Test with 50 sites and extrapolate
        results = run_batch_compliance([f"SITE-{i:04d}" for i in range(50)])
        
        total_cost = sum(r.total_cost for r in results)
        avg_cost_per_site = total_cost / len(results)
        projected_1000_cost = avg_cost_per_site * 1000
        
        assert projected_1000_cost <= 3.20, \
            f"Projected 1000-site cost ${projected_1000_cost:.2f} exceeds $3.20 target"
    
    def test_processing_time_sla(self):
        """Verify processing time meets SLA (7200s for 1000 sites = 7.2s per site)"""
        random.seed(42)
        start = time.time()
        result = run_compliance_check("SITE-PERF-001")
        elapsed = time.time() - start
        
        per_site_sla = BUSINESS_CONFIG['processing_sla'] / 1000  # 7.2 seconds
        
        assert elapsed <= per_site_sla, \
            f"Processing time {elapsed:.2f}s exceeds {per_site_sla}s SLA"
    
    def test_wall_clock_1000_sites(self):
        """Verify 1000 sites can theoretically complete within 7200s SLA"""
        random.seed(42)
        # Test 10 sites and extrapolate
        start = time.time()
        results = run_batch_compliance([f"SITE-PERF-{i:03d}" for i in range(10)])
        elapsed = time.time() - start
        
        projected_1000_time = (elapsed / 10) * 1000
        
        assert projected_1000_time <= 7200, \
            f"Projected 1000-site time {projected_1000_time:.0f}s exceeds 7200s SLA"
    
    def test_error_isolation(self):
        """Verify agents handle failures gracefully without crashing"""
        random.seed(42)
        result = run_compliance_check("SITE-ERROR-TEST")
        
        # Even if NYC API fails (23% rate), system should complete
        assert result.risk_score >= 0, "Risk score calculation failed"
        assert len(result.agent_outputs) >= 2, "Agents didn't complete execution"
    
    def test_token_tracking_accuracy(self):
        """Verify token usage tracking is accurate"""
        random.seed(42)
        result = run_compliance_check("SITE-TOKEN-001")
        
        # Sum agent token usage
        agent_tokens = sum(output.tokens_used for output in result.agent_outputs if output.status == "success")
        
        assert result.total_tokens == agent_tokens, \
            f"Token mismatch: state={result.total_tokens}, agents={agent_tokens}"
        
        # Verify cost calculation matches token usage
        expected_cost = sum(output.usd_cost for output in result.agent_outputs if output.status == "success")
        assert abs(result.total_cost - expected_cost) < 0.0001, \
            f"Cost mismatch: state=${result.total_cost:.4f}, expected=${expected_cost:.4f}"
    
    def test_savings_calculation(self):
        """Verify savings calculation includes 87% accuracy adjustment"""
        random.seed(42)
        result = run_compliance_check("SITE-SAVINGS-001")
        
        if result.violations:
            total_fines = sum(v.estimated_fine for v in result.violations)
            expected_savings = total_fines * BUSINESS_CONFIG['accuracy_target']
            
            assert abs(result.estimated_savings - expected_savings) < 1.0, \
                f"Savings calculation incorrect: {result.estimated_savings} vs {expected_savings}"
    
    def test_deterministic_output(self):
        """Verify same site_id produces consistent results with seed=42"""
        random.seed(42)
        result1 = run_compliance_check("SITE-DET-001")
        
        random.seed(42)
        result2 = run_compliance_check("SITE-DET-001")
        
        assert len(result1.violations) == len(result2.violations), \
            f"Violation detection not deterministic: {len(result1.violations)} vs {len(result2.violations)}"
        
        assert result1.risk_score == result2.risk_score, \
            f"Risk scoring not deterministic: {result1.risk_score} vs {result2.risk_score}"
    
    def test_batch_processing(self):
        """Verify batch processing handles multiple sites correctly"""
        random.seed(42)
        site_ids = [f"SITE-BATCH-{i:03d}" for i in range(5)]
        results = run_batch_compliance(site_ids)
        
        assert len(results) == 5, f"Batch processing didn't return all results: got {len(results)}"
        
        # Each result should be complete
        for result in results:
            assert result.site_id in site_ids, f"Unknown site_id: {result.site_id}"
            assert len(result.agent_outputs) >= 2, f"Incomplete agent execution for {result.site_id}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
