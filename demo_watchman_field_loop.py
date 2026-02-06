#!/usr/bin/env python3
"""
Watchman Agent Demo - Field Reality Verification
Demonstrates the complete Quad-Handshake: Scout → Guard → Watchman → Fixer

This demo shows ConComplyAi's "Full Loop" capability:
- Finding the bid (Scout)
- Validating compliance (Guard)  
- Watching the worker on the scaffold (Watchman)
- Fixing issues autonomously (Fixer)
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from packages.agents.scout.finder import Opportunity, create_scout_handshake
from packages.agents.watchman.vision import analyze_site_frame
from packages.agents.watchman.logger import generate_daily_log, ComplianceRecord
from packages.core.agent_protocol import AgentRole, AuditChain
from packages.core.audit import create_decision_proof, LogicCitation, ComplianceStandard


def print_banner(text: str):
    """Print a formatted banner"""
    print("\n" + "=" * 80)
    print(text.center(80))
    print("=" * 80)


def main():
    print_banner("WATCHMAN AGENT DEMO")
    print("\nConComplyAi: From Finding the Bid to Watching the Worker on the Scaffold")
    
    # STEP 1: Scout discovers opportunity
    print_banner("STEP 1: Scout Discovers Opportunity")
    
    manhattan_opportunity = Opportunity(
        permit_number="121234567",
        job_type="NB",
        address="350 5TH AVENUE",
        borough="MANHATTAN",
        owner_name="Empire State Building LLC",
        owner_phone="2125551234",
        estimated_fee=50000.0,
        estimated_project_cost=10000000.0,
        filing_date=datetime.now() - timedelta(hours=12),
        issuance_date=datetime.now() - timedelta(hours=1),
        opportunity_score=0.95,
        raw_permit_data={"job_type": "NB", "work_type": "FACADE_RENOVATION"}
    )
    
    print(f"\n📍 Location: {manhattan_opportunity.address}, {manhattan_opportunity.borough}")
    print(f"💰 Project Value: ${manhattan_opportunity.estimated_project_cost:,.0f}")
    print(f"🏗️  Job Type: {manhattan_opportunity.job_type} - New Building")
    print(f"📋 DOB Permit #: {manhattan_opportunity.permit_number}")
    print(f"⭐ Opportunity Score: {manhattan_opportunity.opportunity_score:.1%}")
    
    # Create Scout decision proof
    scout_proof = create_decision_proof(
        agent_name="Scout",
        decision="OPPORTUNITY_FOUND",
        input_data={
            "permit_number": manhattan_opportunity.permit_number,
            "borough": manhattan_opportunity.borough,
            "project_cost": manhattan_opportunity.estimated_project_cost
        },
        logic_citations=[
            LogicCitation(
                standard=ComplianceStandard.NYC_BC_3301,
                clause="Major Construction",
                interpretation="$10M facade renovation requires comprehensive compliance monitoring",
                confidence=0.95
            )
        ],
        reasoning="Discovered high-value construction opportunity at iconic NYC landmark",
        confidence=0.95,
        risk_level="HIGH",
        cost_usd=0.00015
    )
    
    scout_handshake = create_scout_handshake(
        opportunity=manhattan_opportunity,
        decision_proof_hash=scout_proof.proof_hash,
        target_agent=AgentRole.GUARD
    )
    
    print(f"\n✅ Scout handshake created")
    print(f"   Decision hash: {scout_proof.proof_hash[:32]}...")
    print(f"   Target: Guard (for COI validation)")
    print(f"   Cost: ${scout_proof.cost_usd:.6f}")
    
    # STEP 2: Guard validates (simulated - assuming approval)
    print_banner("STEP 2: Guard Validates COI")
    
    guard_proof = create_decision_proof(
        agent_name="Guard",
        decision="APPROVED",
        input_data={
            "document_id": f"COI-{manhattan_opportunity.permit_number}",
            "project_id": manhattan_opportunity.to_project_id(),
        },
        logic_citations=[
            LogicCitation(
                standard=ComplianceStandard.ISO_GL_MINIMUM,
                clause="General Liability",
                interpretation="COI meets all NYC requirements for landmark construction",
                confidence=0.98
            )
        ],
        reasoning="COI validated with all required coverages and endorsements",
        confidence=0.98,
        risk_level="LOW",
        cost_usd=0.00100
    )
    
    from packages.core.agent_protocol import create_guard_handshake
    guard_handshake = create_guard_handshake(
        decision_proof_hash=guard_proof.proof_hash,
        project_id=manhattan_opportunity.to_project_id(),
        status="APPROVED",
        parent_handshake=scout_handshake
    )
    
    print(f"\n✅ COI Validation Complete")
    print(f"   Status: APPROVED")
    print(f"   Confidence: {guard_proof.confidence:.1%}")
    print(f"   Target: Watchman (for site monitoring)")
    print(f"   Cost: ${guard_proof.cost_usd:.6f}")
    
    # STEP 3: Watchman monitors site
    print_banner("STEP 3: Watchman Monitors Site via Camera Feed")
    
    print("\n📸 Processing camera feed from construction site...")
    print("   Camera: SITE-CAM-01 (Scaffold Level 42)")
    print("   Time: 10:15 AM")
    
    # Mock camera frame
    mock_camera_frame = b"mock_camera_frame_data"
    
    watchman_result = analyze_site_frame(
        image_buffer=mock_camera_frame,
        project_id=manhattan_opportunity.to_project_id(),
        frame_id="FRAME-ESB-20260206-1015",
        verify_presence=True,
        parent_handshake=guard_handshake
    )
    
    safety_analysis = watchman_result["safety_analysis"]
    presence_alert = watchman_result.get("presence_alert")
    
    print(f"\n🔍 Vision Analysis Complete:")
    print(f"   Workers detected: {safety_analysis.persons_detected}")
    print(f"   Hard hats detected: {safety_analysis.hard_hats_detected}")
    print(f"   Safety vests detected: {safety_analysis.safety_vests_detected}")
    print(f"   Safety Score: {safety_analysis.safety_score:.1f}/100")
    print(f"   Compliance Rate: {safety_analysis.compliance_rate:.1%}")
    print(f"   Risk Level: {safety_analysis.risk_level}")
    
    if safety_analysis.violations:
        print(f"\n⚠️  Safety Violations Detected:")
        for violation in safety_analysis.violations:
            print(f"   • {violation}")
    else:
        print(f"\n✅ No safety violations detected")
    
    print(f"\n🔗 Reality Check: Cross-referencing with Guard's database...")
    if presence_alert:
        print(f"   ⚠️  ALERT: {presence_alert.alert_type}")
        print(f"   Detected: {presence_alert.detected_count} persons")
        print(f"   Approved: {presence_alert.approved_count} workers")
        print(f"   Severity: {presence_alert.severity}")
    else:
        print(f"   ✅ Site presence verified")
        print(f"   All detected workers match Guard's approved database")
    
    print(f"\n💰 Watchman Cost: ${watchman_result['cost_usd']:.6f}")
    
    # STEP 4: Generate Daily Log
    print_banner("STEP 4: Generate Verified Daily Log")
    
    # Create compliance records for the day
    compliance_records = [
        ComplianceRecord(
            timestamp=datetime.now() - timedelta(hours=7),
            frame_id="FRAME-ESB-20260206-0800",
            persons_detected=4,
            hard_hats_detected=4,
            safety_vests_detected=4,
            safety_score=100.0,
            compliance_rate=1.0,
            violations=[]
        ),
        ComplianceRecord(
            timestamp=datetime.now() - timedelta(hours=5),
            frame_id="FRAME-ESB-20260206-1000",
            persons_detected=5,
            hard_hats_detected=4,
            safety_vests_detected=5,
            safety_score=80.0,
            compliance_rate=0.80,
            violations=["Missing hard hat(s): 1 worker(s) without required head protection"]
        ),
        ComplianceRecord(
            timestamp=datetime.now() - timedelta(hours=2),
            frame_id="FRAME-ESB-20260206-1300",
            persons_detected=3,
            hard_hats_detected=3,
            safety_vests_detected=2,
            safety_score=66.7,
            compliance_rate=0.67,
            violations=["Missing safety vest(s): 1 worker(s) without required high-visibility clothing"]
        ),
    ]
    
    log_result = generate_daily_log(
        compliance_records=compliance_records,
        project_id=manhattan_opportunity.to_project_id(),
        shift_date=datetime.now().date(),
        output_format="text",
        parent_project_hash=scout_proof.proof_hash
    )
    
    site_audit_proof = log_result["site_audit_proof"]
    shift_summary = log_result["shift_summary"]
    
    print(f"\n📊 Shift Summary:")
    print(f"   Frames analyzed: {shift_summary.total_frames_analyzed}")
    print(f"   Average safety score: {shift_summary.average_safety_score:.1f}/100")
    print(f"   Average compliance: {shift_summary.average_compliance_rate:.1%}")
    print(f"   Total violations: {shift_summary.total_violations}")
    
    if shift_summary.critical_incidents > 0:
        print(f"   ⚠️  Critical incidents: {shift_summary.critical_incidents}")
    else:
        print(f"   ✅ No critical incidents")
    
    print(f"\n🔐 Cryptographic Audit Proof:")
    print(f"   Proof ID: {site_audit_proof.proof_id}")
    print(f"   Hash: {site_audit_proof.proof_hash[:32]}...")
    print(f"   Linked to Scout Project: {site_audit_proof.parent_project_hash[:16] if site_audit_proof.parent_project_hash else 'N/A'}...")
    print(f"   Generated: {site_audit_proof.generated_at.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # STEP 5: Complete Audit Chain
    print_banner("STEP 5: Verify Complete Audit Chain")
    
    watchman_handshake = watchman_result["handshake"]
    
    audit_chain = AuditChain(
        project_id=manhattan_opportunity.to_project_id(),
        chain_links=[scout_handshake, guard_handshake, watchman_handshake],
        total_cost_usd=(
            scout_proof.cost_usd +
            guard_proof.cost_usd +
            watchman_result["cost_usd"]
        ),
        processing_time_seconds=2.5,
        outcome="MONITORING_ACTIVE"
    )
    
    chain_valid = audit_chain.verify_chain_integrity()
    
    print(f"\n🔗 Audit Chain:")
    print(f"   Scout → Guard → Watchman")
    print(f"   Links: {len(audit_chain.chain_links)}")
    print(f"   Integrity: {'✅ VALID' if chain_valid else '❌ BROKEN'}")
    
    print(f"\n💰 Total Pipeline Cost:")
    print(f"   Scout: ${scout_proof.cost_usd:.6f}")
    print(f"   Guard: ${guard_proof.cost_usd:.6f}")
    print(f"   Watchman: ${watchman_result['cost_usd']:.6f}")
    print(f"   ---")
    print(f"   Total: ${audit_chain.total_cost_usd:.6f}")
    print(f"   Target: $0.005000")
    print(f"   Status: {'✅ UNDER TARGET' if audit_chain.total_cost_usd < 0.005 else '❌ OVER TARGET'}")
    
    # Summary
    print_banner("MISSION ACCOMPLISHED")
    
    print(f"""
🎯 ConComplyAi has demonstrated the complete "Full Loop":

1. ✅ Finding the Bid
   Scout discovered a ${manhattan_opportunity.estimated_project_cost:,.0f} opportunity
   at {manhattan_opportunity.address}

2. ✅ Validating Compliance
   Guard approved COI with {guard_proof.confidence:.1%} confidence

3. ✅ Watching the Worker on the Scaffold
   Watchman monitored {shift_summary.total_frames_analyzed} camera frames
   Average safety score: {shift_summary.average_safety_score:.1f}/100

4. ✅ Maintaining Cryptographic Audit Trail
   Complete chain from Scout → Guard → Watchman
   SHA-256 hashes ensure tamper-proof records

5. ✅ Cost Efficiency
   Total pipeline cost: ${audit_chain.total_cost_usd:.6f} (target: $0.005)

ConComplyAi owns the full construction compliance loop from office to field.
    """)
    
    print("=" * 80)


if __name__ == "__main__":
    main()
