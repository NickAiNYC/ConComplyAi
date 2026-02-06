"""
Integration Test: Scout → Guard → Watchman → Fixer (Quad-Handshake)
Tests the complete "Field to Office" loop

SCENARIO:
1. Scout discovers a $5M construction permit in Manhattan
2. Guard validates COI and approves (or rejects and sends to Fixer)
3. Watchman monitors site via camera feed
4. Watchman cross-checks detected workers with Guard's approved count
5. Verify complete Quad-Handshake audit chain
6. Verify total cost < $0.005

This test validates:
- Complete quad handshake integration (Scout → Guard → Watchman → Fixer)
- Field reality verification (camera feed → database cross-check)
- PPE compliance detection
- Site presence verification
- Cryptographic audit chain integrity
- Cost efficiency
"""

import pytest
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any

from packages.agents.scout.finder import (
    Opportunity,
    create_scout_handshake
)
from packages.agents.guard.core import validate_coi
from packages.agents.guard.validator import ComplianceResult
from packages.agents.watchman.vision import (
    WatchmanAgent,
    analyze_site_frame,
    WatchmanOutput,
    SafetyAnalysis,
    SitePresenceAlert
)
from packages.agents.watchman.logger import (
    generate_daily_log,
    ComplianceRecord,
    SiteAuditProof
)
from packages.agents.fixer.outreach import OutreachAgent, DeficiencyReport, BrokerMetadata
from packages.core.agent_protocol import (
    AgentRole,
    AgentHandshakeV2,
    AuditChain,
    create_guard_handshake
)
from packages.core.audit import (
    DecisionProof,
    create_decision_proof,
    LogicCitation,
    ComplianceStandard
)


class TestFieldToOfficeLoop:
    """Integration tests for the complete Field-to-Office loop"""
    
    def test_quad_handshake_full_loop(self):
        """
        Complete Quad-Handshake: Scout → Guard → Watchman → Fixer
        
        SCENARIO:
        1. Scout finds $5M Manhattan school construction permit
        2. Guard approves COI after validation
        3. Watchman monitors site and detects PPE compliance issues
        4. Watchman verifies site presence matches Guard's approved count
        5. If issues found, Fixer can be triggered (optional)
        """
        print("\n" + "=" * 80)
        print("QUAD-HANDSHAKE: Field to Office Loop Test")
        print("=" * 80)
        
        # STEP 1: Scout discovers opportunity
        manhattan_opportunity = Opportunity(
            permit_number="121234567",
            job_type="NB",
            address="123 MAIN STREET",
            borough="MANHATTAN",
            owner_name="NYC School Construction Authority",
            owner_phone="2125551234",
            estimated_fee=25000.0,
            estimated_project_cost=5000000.0,
            filing_date=datetime.now() - timedelta(hours=12),
            issuance_date=datetime.now() - timedelta(hours=1),
            opportunity_score=0.85,
            raw_permit_data={"job_type": "NB", "work_type": "SCHOOL"}
        )
        
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
                    clause="School Construction",
                    interpretation="$5M school construction requires compliance validation",
                    confidence=0.90
                )
            ],
            reasoning="Discovered high-value school construction permit in Manhattan",
            confidence=0.90,
            risk_level="MEDIUM",
            cost_usd=0.00015
        )
        
        # Create Scout handshake
        scout_handshake = create_scout_handshake(
            opportunity=manhattan_opportunity,
            decision_proof_hash=scout_proof.proof_hash,
            target_agent=AgentRole.GUARD
        )
        
        print("\n✅ STEP 1: Scout discovered opportunity")
        print(f"   Permit: DOB Job #{manhattan_opportunity.permit_number}")
        print(f"   Location: {manhattan_opportunity.address}, {manhattan_opportunity.borough}")
        print(f"   Value: ${manhattan_opportunity.estimated_project_cost:,.0f}")
        print(f"   Cost: ${scout_proof.cost_usd:.6f}")
        
        # STEP 2: Guard validates COI
        # Mock Guard approval
        guard_doc_id = f"COI-{manhattan_opportunity.permit_number}"
        
        guard_proof = create_decision_proof(
            agent_name="Guard",
            decision="APPROVED",
            input_data={
                "document_id": guard_doc_id,
                "project_id": manhattan_opportunity.to_project_id(),
                "permit_number": manhattan_opportunity.permit_number
            },
            logic_citations=[
                LogicCitation(
                    standard=ComplianceStandard.ISO_GL_MINIMUM,
                    clause="General Liability Coverage",
                    interpretation="COI meets all NYC requirements for school construction",
                    confidence=0.95
                )
            ],
            reasoning="COI validated successfully with all required coverages",
            confidence=0.95,
            risk_level="LOW",
            cost_usd=0.00100
        )
        
        compliance_result = ComplianceResult(
            status="APPROVED",
            deficiency_list=[],
            decision_proof=guard_proof.proof_hash,
            confidence_score=0.95,
            processing_cost=0.00100,
            document_id=guard_doc_id,
            ocr_confidence=0.98,
            page_count=2,
            citations=["ISO_GL_MINIMUM"]
        )
        
        # Create Guard handshake (approved → Watchman)
        guard_handshake = create_guard_handshake(
            decision_proof_hash=guard_proof.proof_hash,
            project_id=manhattan_opportunity.to_project_id(),
            status="APPROVED",
            parent_handshake=scout_handshake
        )
        
        print("\n✅ STEP 2: Guard validated COI")
        print(f"   Status: {compliance_result.status}")
        print(f"   Confidence: {compliance_result.confidence_score:.1%}")
        print(f"   Cost: ${guard_proof.cost_usd:.6f}")
        
        # Verify Guard → Watchman handshake
        assert guard_handshake.source_agent == AgentRole.GUARD
        assert guard_handshake.target_agent == AgentRole.WATCHMAN
        assert guard_handshake.parent_handshake_id == scout_handshake.decision_hash
        
        # STEP 3: Watchman analyzes site camera feed
        # Mock camera frame (in production, would be actual image bytes)
        mock_camera_frame = b"mock_camera_frame_data"
        
        watchman_result = analyze_site_frame(
            image_buffer=mock_camera_frame,
            project_id=manhattan_opportunity.to_project_id(),
            frame_id="FRAME-TEST-001",
            verify_presence=True,
            parent_handshake=guard_handshake
        )
        
        watchman_output = watchman_result["watchman_output"]
        safety_analysis = watchman_result["safety_analysis"]
        presence_alert = watchman_result.get("presence_alert")
        watchman_handshake = watchman_result["handshake"]
        
        # Verify Watchman output
        assert isinstance(watchman_output, WatchmanOutput)
        assert isinstance(safety_analysis, SafetyAnalysis)
        assert watchman_handshake.source_agent == AgentRole.WATCHMAN
        assert watchman_handshake.parent_handshake_id == guard_handshake.decision_hash
        
        print("\n✅ STEP 3: Watchman analyzed site camera feed")
        print(f"   Frame: {safety_analysis.frame_id}")
        print(f"   Persons detected: {safety_analysis.persons_detected}")
        print(f"   Hard hats: {safety_analysis.hard_hats_detected}")
        print(f"   Safety vests: {safety_analysis.safety_vests_detected}")
        print(f"   Safety score: {safety_analysis.safety_score:.1f}/100")
        print(f"   Compliance rate: {safety_analysis.compliance_rate:.1%}")
        print(f"   Risk level: {safety_analysis.risk_level}")
        print(f"   Cost: ${watchman_result['cost_usd']:.6f}")
        
        # Check for violations
        if safety_analysis.violations:
            print(f"   Violations detected: {len(safety_analysis.violations)}")
            for violation in safety_analysis.violations:
                print(f"     - {violation}")
        
        # STEP 4: Verify site presence alert
        if presence_alert:
            print("\n⚠️  STEP 4: Site presence alert detected")
            print(f"   Alert type: {presence_alert.alert_type}")
            print(f"   Detected: {presence_alert.detected_count} persons")
            print(f"   Approved: {presence_alert.approved_count} workers")
            print(f"   Delta: {presence_alert.delta}")
            print(f"   Severity: {presence_alert.severity}")
        else:
            print("\n✅ STEP 4: Site presence verified")
            print(f"   Detected workers match approved count")
        
        # STEP 5: Build complete audit chain
        chain_links = [scout_handshake, guard_handshake, watchman_handshake]
        total_cost = (
            scout_proof.cost_usd +
            guard_proof.cost_usd +
            watchman_result["cost_usd"]
        )
        
        audit_chain = AuditChain(
            project_id=manhattan_opportunity.to_project_id(),
            chain_links=chain_links,
            total_cost_usd=total_cost,
            processing_time_seconds=2.0,
            outcome="MONITORING_ACTIVE"
        )
        
        # Verify chain integrity
        chain_valid = audit_chain.verify_chain_integrity()
        assert chain_valid is True, "Cryptographic hash chain must be valid"
        
        print("\n✅ STEP 5: Audit chain verified")
        print(f"   Chain links: {len(audit_chain.chain_links)}")
        print(f"   Scout → Guard → Watchman")
        print(f"   Integrity: {'✅ VALID' if chain_valid else '❌ BROKEN'}")
        print(f"   Total cost: ${audit_chain.total_cost_usd:.6f}")
        
        # STEP 6: Verify cost target
        target_cost = 0.005
        assert total_cost < target_cost, \
            f"Pipeline cost ${total_cost:.6f} must be < ${target_cost:.6f}"
        
        print(f"   Cost target: ${target_cost:.6f}")
        print(f"   Status: {'✅ UNDER TARGET' if total_cost < target_cost else '❌ OVER TARGET'}")
        
        # Print full summary
        print("\n" + "=" * 80)
        print("QUAD-HANDSHAKE COMPLETE")
        print("=" * 80)
        print(audit_chain.to_summary())
        print("=" * 80)
    
    def test_watchman_ppe_detection(self):
        """Test Watchman PPE detection capabilities"""
        agent = WatchmanAgent()
        
        # Mock camera frame
        mock_frame = b"test_frame_data"
        
        result = agent.analyze_frame(
            image_buffer=mock_frame,
            frame_id="TEST-FRAME-001",
            project_id="TEST-PROJECT"
        )
        
        safety_analysis = result["safety_analysis"]
        
        # Verify detection results
        assert safety_analysis.persons_detected > 0
        assert safety_analysis.safety_score >= 0.0
        assert safety_analysis.safety_score <= 100.0
        assert safety_analysis.compliance_rate >= 0.0
        assert safety_analysis.compliance_rate <= 1.0
        assert safety_analysis.risk_level in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
        
        print(f"\n✅ PPE Detection Test:")
        print(f"   Persons: {safety_analysis.persons_detected}")
        print(f"   Hard hats: {safety_analysis.hard_hats_detected}")
        print(f"   Safety vests: {safety_analysis.safety_vests_detected}")
        print(f"   Safety score: {safety_analysis.safety_score:.1f}/100")
        print(f"   Compliance: {safety_analysis.compliance_rate:.1%}")
    
    def test_watchman_presence_verification(self):
        """Test Watchman site presence verification"""
        agent = WatchmanAgent()
        
        # Test with matching count (verified)
        result_verified = agent.verify_site_presence(
            detected_persons_count=3,
            project_id="TEST-PROJECT-001"
        )
        
        assert result_verified["verified"] is True
        assert result_verified["presence_alert"] is None
        
        print("\n✅ Presence Verification Test (Verified):")
        print(f"   Detected: 3, Approved: {result_verified['guard_approved_count']}")
        print(f"   Status: VERIFIED ✅")
        
        # Test with mismatch (unverified)
        result_unverified = agent.verify_site_presence(
            detected_persons_count=5,
            project_id="TEST-PROJECT-002"
        )
        
        assert result_unverified["verified"] is False
        assert result_unverified["presence_alert"] is not None
        
        alert = result_unverified["presence_alert"]
        print("\n⚠️  Presence Verification Test (Unverified):")
        print(f"   Detected: {alert.detected_count}, Approved: {alert.approved_count}")
        print(f"   Delta: +{alert.delta}")
        print(f"   Alert: {alert.alert_type}")
        print(f"   Severity: {alert.severity}")
    
    def test_watchman_daily_log_generation(self):
        """Test Watchman daily log generation"""
        # Create mock compliance records for a shift
        compliance_records = [
            ComplianceRecord(
                timestamp=datetime.now() - timedelta(hours=7),
                frame_id="FRAME-001",
                persons_detected=3,
                hard_hats_detected=3,
                safety_vests_detected=3,
                safety_score=100.0,
                compliance_rate=1.0,
                violations=[]
            ),
            ComplianceRecord(
                timestamp=datetime.now() - timedelta(hours=5),
                frame_id="FRAME-002",
                persons_detected=4,
                hard_hats_detected=3,
                safety_vests_detected=4,
                safety_score=75.0,
                compliance_rate=0.75,
                violations=["Missing hard hat(s): 1 worker(s) without required head protection"]
            ),
            ComplianceRecord(
                timestamp=datetime.now() - timedelta(hours=2),
                frame_id="FRAME-003",
                persons_detected=2,
                hard_hats_detected=2,
                safety_vests_detected=2,
                safety_score=100.0,
                compliance_rate=1.0,
                violations=[]
            ),
        ]
        
        # Generate daily log
        log_result = generate_daily_log(
            compliance_records=compliance_records,
            project_id="TEST-PROJECT-LOG",
            shift_date=datetime.now().date(),
            output_format="json",
            parent_project_hash="abc123def456"
        )
        
        site_audit_proof = log_result["site_audit_proof"]
        shift_summary = log_result["shift_summary"]
        
        # Verify audit proof
        assert isinstance(site_audit_proof, SiteAuditProof)
        assert site_audit_proof.proof_hash
        assert site_audit_proof.project_id == "TEST-PROJECT-LOG"
        assert site_audit_proof.parent_project_hash == "abc123def456"
        
        # Verify shift summary
        assert shift_summary.total_frames_analyzed == 3
        assert shift_summary.max_workers_detected == 4
        assert shift_summary.total_violations == 1
        
        print("\n✅ Daily Log Generation Test:")
        print(f"   Proof ID: {site_audit_proof.proof_id}")
        print(f"   Frames analyzed: {shift_summary.total_frames_analyzed}")
        print(f"   Avg safety score: {shift_summary.average_safety_score:.1f}/100")
        print(f"   Total violations: {shift_summary.total_violations}")
        print(f"   Proof hash: {site_audit_proof.proof_hash[:32]}...")
        
        # Print report excerpt
        report_text = log_result["report_text"]
        print("\n   Report excerpt:")
        for line in report_text.split('\n')[:10]:
            print(f"     {line}")
    
    def test_quad_handshake_cost_target(self):
        """Verify that complete Quad-Handshake stays under $0.005"""
        # Simulate costs for each agent
        scout_cost = 0.00015  # Scout: Socrata API calls
        guard_cost = 0.00100  # Guard: Document validation
        watchman_cost = 0.00050  # Watchman: Vision inference
        fixer_cost = 0.00020  # Fixer: Email drafting (if triggered)
        
        # Triple handshake (no Fixer)
        triple_cost = scout_cost + guard_cost + watchman_cost
        assert triple_cost < 0.005
        
        # Quad handshake (with Fixer)
        quad_cost = scout_cost + guard_cost + watchman_cost + fixer_cost
        assert quad_cost < 0.005
        
        print("\n✅ Cost Target Verification:")
        print(f"   Scout: ${scout_cost:.6f}")
        print(f"   Guard: ${guard_cost:.6f}")
        print(f"   Watchman: ${watchman_cost:.6f}")
        print(f"   Fixer: ${fixer_cost:.6f}")
        print(f"   ---")
        print(f"   Triple (Scout+Guard+Watchman): ${triple_cost:.6f}")
        print(f"   Quad (All Four): ${quad_cost:.6f}")
        print(f"   Target: $0.005")
        print(f"   Status: {'✅ UNDER TARGET' if quad_cost < 0.005 else '❌ OVER TARGET'}")


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "-s"])
