#!/usr/bin/env python3
"""
Demo: Scout → Guard Agent Handshake Workflow
Demonstrates the complete AgentHandshakeV2 workflow from permit discovery to COI validation
"""
import sys
from pathlib import Path

# Add packages to path
sys.path.insert(0, str(Path(__file__).parent))

from packages.agents.scout.finder import (
    find_opportunities,
    create_scout_handshake,
)
from packages.agents.guard.core import validate_coi
from packages.core.agent_protocol import AgentRole, AuditChain


def main():
    print("=" * 80)
    print("SCOUT → GUARD AGENT HANDSHAKE DEMO")
    print("=" * 80)
    print()
    
    # STEP 1: Scout discovers opportunities
    print("🔍 STEP 1: Scout Agent discovering NYC permit opportunities...")
    print("-" * 80)
    
    scout_result = find_opportunities(
        hours_lookback=24,
        min_estimated_fee=5000.0,
        job_types=["NB", "A1"],
        use_mock=True
    )
    
    opportunities = scout_result["opportunities"]
    scout_proof = scout_result["decision_proof"]
    
    print(f"✅ Scout discovered {len(opportunities)} opportunities")
    print(f"   Total permits scanned: {scout_result['total_permits_scanned']}")
    print(f"   Veteran Skeptic filter: ${scout_result['search_criteria']['min_estimated_fee']:,.0f} minimum")
    print(f"   Scout cost: ${scout_result['cost_usd']:.6f}")
    print()
    
    # Show opportunities
    print("📋 Opportunities Found:")
    for i, opp in enumerate(opportunities, 1):
        print(f"   {i}. {opp.owner_name}")
        print(f"      Permit: {opp.permit_number} ({opp.job_type})")
        print(f"      Location: {opp.address}, {opp.borough}")
        print(f"      Est. Project Cost: ${opp.estimated_project_cost:,.0f}")
        print(f"      Opportunity Score: {opp.opportunity_score:.2f}")
        print()
    
    # Select first SCA opportunity
    sca_opportunity = None
    for opp in opportunities:
        if "school" in opp.owner_name.lower() or "sca" in opp.owner_name.lower():
            sca_opportunity = opp
            break
    
    if sca_opportunity is None:
        sca_opportunity = opportunities[0]
    
    print(f"🎯 Selected opportunity: {sca_opportunity.owner_name}")
    print(f"   Project ID: {sca_opportunity.to_project_id()}")
    print()
    
    # STEP 2: Scout creates handshake
    print("🤝 STEP 2: Scout creating handshake for Guard...")
    print("-" * 80)
    
    scout_handshake = create_scout_handshake(
        opportunity=sca_opportunity,
        decision_proof_hash=scout_proof.proof_hash,
        target_agent=AgentRole.GUARD
    )
    
    print(f"✅ Handshake created")
    print(f"   Source: {scout_handshake.source_agent.value}")
    print(f"   Target: {scout_handshake.target_agent.value}")
    print(f"   Project: {scout_handshake.project_id}")
    print(f"   Decision Hash: {scout_handshake.decision_hash[:16]}...")
    print(f"   Reason: {scout_handshake.transition_reason}")
    print()
    
    # STEP 3: Guard validates COI
    print("🛡️  STEP 3: Guard Agent validating Certificate of Insurance...")
    print("-" * 80)
    
    mock_coi_path = Path("/tmp/sca_project_compliant_coi.pdf")
    
    guard_result = validate_coi(
        pdf_path=mock_coi_path,
        parent_handshake=scout_handshake,
        project_id=sca_opportunity.to_project_id()
    )
    
    compliance_result = guard_result["compliance_result"]
    guard_handshake = guard_result["handshake"]
    guard_proof = guard_result["decision_proof_obj"]
    
    print(f"✅ COI validation complete")
    print(f"   Status: {compliance_result.status}")
    print(f"   Confidence: {compliance_result.confidence_score:.2%}")
    print(f"   OCR Confidence: {compliance_result.ocr_confidence:.2%}")
    print(f"   Page Count: {compliance_result.page_count}")
    print(f"   Guard cost: ${guard_result['cost_usd']:.6f}")
    
    if compliance_result.deficiency_list:
        print(f"   Deficiencies: {len(compliance_result.deficiency_list)}")
        for deficiency in compliance_result.deficiency_list:
            print(f"      - {deficiency}")
    else:
        print(f"   ✓ No deficiencies found")
    
    print()
    print(f"🤝 Guard handshake:")
    print(f"   Source: {guard_handshake.source_agent.value}")
    print(f"   Target: {guard_handshake.target_agent.value if guard_handshake.target_agent else 'TERMINAL'}")
    print(f"   Parent Hash: {guard_handshake.parent_handshake_id[:16]}...")
    print(f"   Decision Hash: {guard_handshake.decision_hash[:16]}...")
    print()
    
    # STEP 4: Build and verify audit chain
    print("🔗 STEP 4: Building and verifying audit chain...")
    print("-" * 80)
    
    total_cost = scout_result["cost_usd"] + guard_result["cost_usd"]
    
    audit_chain = AuditChain(
        project_id=sca_opportunity.to_project_id(),
        chain_links=[scout_handshake, guard_handshake],
        total_cost_usd=total_cost,
        processing_time_seconds=0.5,
        outcome="BID_READY" if compliance_result.status == "APPROVED" else "PENDING_FIX"
    )
    
    chain_valid = audit_chain.verify_chain_integrity()
    
    print(audit_chain.to_summary())
    print()
    
    # STEP 5: Cost analysis
    print("💰 STEP 5: Cost Analysis")
    print("-" * 80)
    print(f"   Scout cost:  ${scout_result['cost_usd']:.6f}")
    print(f"   Guard cost:  ${guard_result['cost_usd']:.6f}")
    print(f"   Total cost:  ${total_cost:.6f}")
    print(f"   Target:      $0.007000")
    
    if total_cost < 0.007:
        print(f"   Status:      ✅ UNDER TARGET (${0.007 - total_cost:.6f} under)")
    else:
        print(f"   Status:      ⚠️  OVER TARGET (${total_cost - 0.007:.6f} over)")
    
    print()
    
    # STEP 6: Summary
    print("=" * 80)
    print("DEMO SUMMARY")
    print("=" * 80)
    print(f"✅ Scout discovered {len(opportunities)} opportunities")
    print(f"✅ Scout created handshake for {sca_opportunity.owner_name}")
    print(f"✅ Guard validated COI: {compliance_result.status}")
    print(f"✅ Audit chain verified: {'VALID' if chain_valid else 'INVALID'}")
    print(f"✅ Cost efficiency: ${total_cost:.6f}/doc (target: $0.007000)")
    print()
    print("🎉 Scout → Guard handshake workflow successful!")
    print("=" * 80)


if __name__ == "__main__":
    main()
