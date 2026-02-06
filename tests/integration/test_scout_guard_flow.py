"""
Integration Test: Scout → Guard Handshake Flow
Tests the complete AgentHandshakeV2 workflow from opportunity discovery to COI validation

This test demonstrates:
1. Scout discovers a mock SCA project permit
2. Scout creates a HandshakeV2 object with permit data
3. Scout hands off to Guard
4. Guard validates a mock COI against permit requirements
5. AuditChain is verified for integrity
"""
import pytest
from pathlib import Path
from datetime import datetime, timedelta

from packages.agents.scout.finder import (
    find_opportunities,
    create_scout_handshake,
    Opportunity
)
from packages.agents.guard.core import validate_coi, GuardOutput
from packages.core.agent_protocol import (
    AgentRole,
    AgentHandshakeV2,
    AuditChain
)


class TestScoutGuardFlow:
    """Integration tests for Scout → Guard agent handoff"""
    
    def test_scout_discovers_opportunities(self):
        """Test Scout can discover NYC permit opportunities"""
        # Run Scout with mock data
        result = find_opportunities(
            hours_lookback=24,
            min_estimated_fee=5000.0,
            job_types=["NB", "A1"],
            use_mock=True
        )
        
        # Verify Scout found opportunities
        assert "opportunities" in result
        opportunities = result["opportunities"]
        assert len(opportunities) > 0, "Scout should find at least one opportunity"
        
        # Verify opportunities have required fields
        for opp in opportunities:
            assert isinstance(opp, Opportunity)
            assert opp.permit_number
            assert opp.job_type in ["NB", "A1"]
            assert opp.estimated_fee >= 5000.0  # Veteran Skeptic filter
            assert opp.address
            assert opp.owner_name
        
        # Verify decision proof was created
        assert "decision_proof" in result
        assert result["decision_proof"].proof_hash
        
        # Verify cost tracking
        assert "input_tokens" in result
        assert "output_tokens" in result
    
    def test_scout_filters_low_value_permits(self):
        """Test Veteran Skeptic filter removes permits under $5k"""
        result = find_opportunities(
            hours_lookback=24,
            min_estimated_fee=5000.0,
            use_mock=True
        )
        
        opportunities = result["opportunities"]
        
        # All opportunities should meet minimum fee threshold
        for opp in opportunities:
            assert opp.estimated_fee >= 5000.0, \
                f"Permit {opp.permit_number} has fee ${opp.estimated_fee:.2f} < $5000"
    
    def test_scout_creates_handshake(self):
        """Test Scout creates valid AgentHandshakeV2 objects"""
        # Get opportunities from Scout
        result = find_opportunities(use_mock=True)
        opportunities = result["opportunities"]
        assert len(opportunities) > 0
        
        # Get first opportunity
        opportunity = opportunities[0]
        decision_proof = result["decision_proof"]
        
        # Create handshake
        handshake = create_scout_handshake(
            opportunity=opportunity,
            decision_proof_hash=decision_proof.proof_hash,
            target_agent=AgentRole.GUARD
        )
        
        # Verify handshake fields
        assert handshake.source_agent == AgentRole.SCOUT
        assert handshake.target_agent == AgentRole.GUARD
        assert handshake.project_id == opportunity.to_project_id()
        assert handshake.decision_hash == decision_proof.proof_hash
        assert handshake.parent_handshake_id is None  # Scout is first in chain
        assert handshake.transition_reason == "opportunity_discovered"
        
        # Verify metadata contains opportunity details
        assert handshake.metadata["permit_number"] == opportunity.permit_number
        assert handshake.metadata["job_type"] == opportunity.job_type
    
    def test_guard_accepts_handshake(self):
        """Test Guard can accept a handshake from Scout"""
        # Get opportunity from Scout
        scout_result = find_opportunities(use_mock=True)
        opportunities = scout_result["opportunities"]
        assert len(opportunities) > 0
        
        opportunity = opportunities[0]
        scout_proof = scout_result["decision_proof"]
        
        # Create Scout handshake
        scout_handshake = create_scout_handshake(
            opportunity=opportunity,
            decision_proof_hash=scout_proof.proof_hash,
            target_agent=AgentRole.GUARD
        )
        
        # Validate a mock COI with Guard (using parent handshake)
        # Note: We'll use a mock path since we're simulating
        mock_coi_path = Path("/tmp/mock_compliant_coi.pdf")
        
        guard_result = validate_coi(
            pdf_path=mock_coi_path,
            parent_handshake=scout_handshake,
            project_id=opportunity.to_project_id()
        )
        
        # Verify Guard result structure
        assert "compliance_result" in guard_result
        assert "handshake" in guard_result
        assert "guard_output" in guard_result
        
        # Verify Guard handshake links to Scout
        guard_handshake = guard_result["handshake"]
        assert guard_handshake.source_agent == AgentRole.GUARD
        assert guard_handshake.project_id == scout_handshake.project_id
        assert guard_handshake.parent_handshake_id == scout_handshake.decision_hash
        
        # Verify GuardOutput conforms to protocol
        guard_output = guard_result["guard_output"]
        assert isinstance(guard_output, GuardOutput)
        assert guard_output.agent_name == AgentRole.GUARD
        assert guard_output.handshake == guard_handshake
    
    def test_full_scout_guard_pipeline(self):
        """
        Complete integration test: Scout discovery → Guard validation
        
        Simulates:
        1. Scout discovers SCA project permit
        2. Scout hands off to Guard with HandshakeV2
        3. Guard validates mock COI
        4. Audit chain is verified
        """
        # STEP 1: Scout discovers opportunities
        scout_result = find_opportunities(
            hours_lookback=24,
            min_estimated_fee=5000.0,
            use_mock=True
        )
        
        opportunities = scout_result["opportunities"]
        assert len(opportunities) > 0, "Scout should find opportunities"
        
        # Find an SCA opportunity (if available)
        sca_opportunity = None
        for opp in opportunities:
            if "school" in opp.owner_name.lower() or "sca" in opp.owner_name.lower():
                sca_opportunity = opp
                break
        
        if sca_opportunity is None:
            # Use first opportunity
            sca_opportunity = opportunities[0]
        
        scout_proof = scout_result["decision_proof"]
        
        # STEP 2: Scout creates handshake for Guard
        scout_handshake = create_scout_handshake(
            opportunity=sca_opportunity,
            decision_proof_hash=scout_proof.proof_hash,
            target_agent=AgentRole.GUARD
        )
        
        # STEP 3: Guard validates COI with Scout's handshake
        mock_coi_path = Path("/tmp/sca_project_coi_compliant.pdf")
        
        guard_result = validate_coi(
            pdf_path=mock_coi_path,
            parent_handshake=scout_handshake,
            project_id=sca_opportunity.to_project_id()
        )
        
        compliance_result = guard_result["compliance_result"]
        guard_handshake = guard_result["handshake"]
        guard_proof = guard_result["decision_proof_obj"]
        
        # STEP 4: Build and verify audit chain
        audit_chain = AuditChain(
            project_id=sca_opportunity.to_project_id(),
            chain_links=[scout_handshake, guard_handshake],
            total_cost_usd=scout_result["cost_usd"] + guard_result["cost_usd"],
            processing_time_seconds=0.5,  # Mock timing
            outcome="BID_READY" if compliance_result.status == "APPROVED" else "PENDING_FIX"
        )
        
        # STEP 5: Verify audit chain integrity
        chain_valid = audit_chain.verify_chain_integrity()
        assert chain_valid, "Audit chain should have valid linkage"
        
        # Verify chain links properly
        assert len(audit_chain.chain_links) == 2
        assert audit_chain.chain_links[0] == scout_handshake
        assert audit_chain.chain_links[1] == guard_handshake
        
        # Verify parent-child relationship
        assert guard_handshake.parent_handshake_id == scout_handshake.decision_hash
        
        # Print audit summary for demo purposes
        print("\n" + "=" * 80)
        print("SCOUT → GUARD INTEGRATION TEST")
        print("=" * 80)
        print(f"\nOpportunity: {sca_opportunity.owner_name}")
        print(f"Permit: {sca_opportunity.permit_number}")
        print(f"Project Cost: ${sca_opportunity.estimated_project_cost:,.0f}")
        print(f"\nScout → Guard → {guard_handshake.target_agent.value if guard_handshake.target_agent else 'TERMINAL'}")
        print(f"Compliance Status: {compliance_result.status}")
        print(f"\n{audit_chain.to_summary()}")
        print("=" * 80)
    
    def test_cost_efficiency_maintained(self):
        """Verify Scout+Guard pipeline maintains $0.007/doc efficiency"""
        # Run Scout
        scout_result = find_opportunities(use_mock=True)
        scout_cost = scout_result["cost_usd"]
        
        # Run Guard on mock COI
        mock_coi_path = Path("/tmp/mock_coi.pdf")
        guard_result = validate_coi(
            pdf_path=mock_coi_path,
            parent_handshake=None
        )
        guard_cost = guard_result["cost_usd"]
        
        # Total cost
        total_cost = scout_cost + guard_cost
        
        # Verify under target (using $0.007 as per system constraints)
        target_cost = 0.007
        assert total_cost < target_cost, \
            f"Total cost ${total_cost:.6f} exceeds target ${target_cost:.6f}"
        
        print(f"\n💰 Cost Analysis:")
        print(f"   Scout:  ${scout_cost:.6f}")
        print(f"   Guard:  ${guard_cost:.6f}")
        print(f"   Total:  ${total_cost:.6f}")
        print(f"   Target: ${target_cost:.6f}")
        print(f"   Status: ✅ UNDER TARGET" if total_cost < target_cost else "❌ OVER TARGET")
    
    def test_audit_chain_tamper_detection(self):
        """Verify audit chain detects tampering"""
        # Create a valid chain
        scout_result = find_opportunities(use_mock=True)
        opportunities = scout_result["opportunities"]
        opportunity = opportunities[0]
        
        scout_handshake = create_scout_handshake(
            opportunity=opportunity,
            decision_proof_hash=scout_result["decision_proof"].proof_hash,
            target_agent=AgentRole.GUARD
        )
        
        guard_result = validate_coi(
            pdf_path=Path("/tmp/mock.pdf"),
            parent_handshake=scout_handshake
        )
        
        guard_handshake = guard_result["handshake"]
        
        # Create valid chain
        valid_chain = AuditChain(
            project_id=opportunity.to_project_id(),
            chain_links=[scout_handshake, guard_handshake],
            total_cost_usd=0.001,
            processing_time_seconds=0.5,
            outcome="BID_READY"
        )
        
        assert valid_chain.verify_chain_integrity() is True
        
        # Create tampered chain (wrong parent hash)
        tampered_handshake = AgentHandshakeV2(
            source_agent=AgentRole.GUARD,
            target_agent=None,
            project_id=opportunity.to_project_id(),
            decision_hash=guard_result["decision_proof_obj"].proof_hash,
            parent_handshake_id="TAMPERED_HASH_12345",  # Wrong parent
            transition_reason="tampered"
        )
        
        tampered_chain = AuditChain(
            project_id=opportunity.to_project_id(),
            chain_links=[scout_handshake, tampered_handshake],
            total_cost_usd=0.001,
            processing_time_seconds=0.5,
            outcome="BID_READY"
        )
        
        assert tampered_chain.verify_chain_integrity() is False, \
            "Tampered chain should fail verification"


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "-s"])
