"""
Integration Test: Scout → Guard → Fixer Triple Handshake Flow
Tests the complete remediation loop per updated requirements

SCENARIO:
1. Scout finds a $1M electrical permit in Brooklyn
2. Guard rejects the sub's COI for 'Missing Waiver of Subrogation'
3. Fixer produces a valid email draft addressed to the broker on the COI
4. Verify the cryptographic hash chain from Scout through to Fixer

This test validates:
- Full triple handshake integration
- Senior NYC Subcontractor tone
- NYC DOB Job Number inclusion
- Broker metadata handling
- AuditProof generation
- Cost efficiency (< $0.005/opportunity)
"""

import pytest
from pathlib import Path
from datetime import datetime, timedelta

from packages.agents.scout.finder import (
    Opportunity,
    create_scout_handshake
)
from packages.agents.guard.core import validate_coi
from packages.agents.guard.validator import ComplianceResult
from packages.agents.fixer.outreach import (
    OutreachAgent,
    DeficiencyReport,
    BrokerMetadata,
    EmailDraft,
)
from packages.core.agent_protocol import (
    AgentRole,
    AgentHandshakeV2,
    AuditChain,
    create_guard_handshake
)
from packages.core.audit import DecisionProof, create_decision_proof, LogicCitation, ComplianceStandard
from packages.core.workflow_manager import WorkflowManager


class TestTripleHandshakeFlow:
    """Integration tests for Scout → Guard → Fixer triple handshake"""
    
    def test_brooklyn_electrical_permit_scenario(self):
        """
        Full scenario test: Brooklyn $1M electrical permit with missing waiver
        
        SCENARIO:
        1. Scout discovers $1M electrical permit in Brooklyn
        2. Guard validates COI and finds 'Missing Waiver of Subrogation'
        3. Fixer drafts remediation email to broker
        4. Verify complete audit chain integrity
        """
        # STEP 1: Create Scout opportunity for Brooklyn electrical permit
        brooklyn_opportunity = Opportunity(
            permit_number="420241234",
            job_type="A1",
            address="456 ATLANTIC AVENUE",
            borough="BROOKLYN",
            owner_name="Brooklyn Electrical Contractors Inc",
            owner_phone="7185551234",
            estimated_fee=5000.0,
            estimated_project_cost=1000000.0,
            filing_date=datetime.now() - timedelta(hours=12),
            issuance_date=datetime.now() - timedelta(hours=1),
            opportunity_score=0.75,
            raw_permit_data={"job_type": "A1", "work_type": "ELECTRICAL"}
        )
        
        # Create Scout decision proof
        scout_proof = create_decision_proof(
            agent_name="Scout",
            decision="OPPORTUNITY_FOUND",
            input_data={
                "permit_number": brooklyn_opportunity.permit_number,
                "borough": brooklyn_opportunity.borough,
                "project_cost": brooklyn_opportunity.estimated_project_cost
            },
            logic_citations=[
                LogicCitation(
                    standard=ComplianceStandard.NYC_BC_3301,
                    clause="Electrical Work",
                    interpretation="$1M electrical project requires compliance validation",
                    confidence=0.90
                )
            ],
            reasoning="Discovered high-value electrical permit in Brooklyn",
            confidence=0.90,
            risk_level="MEDIUM",
            cost_usd=0.00015
        )
        
        # Create Scout handshake
        scout_handshake = create_scout_handshake(
            opportunity=brooklyn_opportunity,
            decision_proof_hash=scout_proof.proof_hash,
            target_agent=AgentRole.GUARD
        )
        
        assert scout_handshake.source_agent == AgentRole.SCOUT
        assert scout_handshake.target_agent == AgentRole.GUARD
        assert "420241234" in scout_handshake.metadata["permit_number"]
        
        print("\n✅ STEP 1: Scout discovered Brooklyn electrical permit")
        print(f"   Permit: DOB Job #{brooklyn_opportunity.permit_number}")
        print(f"   Location: {brooklyn_opportunity.address}, {brooklyn_opportunity.borough}")
        print(f"   Value: ${brooklyn_opportunity.estimated_project_cost:,.0f}")
        
        # STEP 2: Guard validates COI and finds deficiency
        # Mock Guard rejection for missing waiver
        guard_doc_id = f"COI-BROOKLYN-{datetime.now().strftime('%Y%m%d')}"
        
        guard_proof = create_decision_proof(
            agent_name="Guard",
            decision="REJECTED",
            input_data={
                "document_id": guard_doc_id,
                "project_id": brooklyn_opportunity.to_project_id(),
                "permit_number": brooklyn_opportunity.permit_number
            },
            logic_citations=[
                LogicCitation(
                    standard=ComplianceStandard.WAIVER_SUBROGATION,
                    clause="Standard Waiver",
                    interpretation="Waiver of Subrogation is required for NYC electrical work",
                    confidence=0.95
                )
            ],
            reasoning="COI missing required Waiver of Subrogation endorsement",
            confidence=0.92,
            risk_level="HIGH",
            cost_usd=0.00100
        )
        
        compliance_result = ComplianceResult(
            status="REJECTED",
            deficiency_list=["Missing Waiver of Subrogation"],
            decision_proof=guard_proof.proof_hash,
            confidence_score=0.92,
            processing_cost=0.00100,
            document_id=guard_doc_id,
            ocr_confidence=0.96,
            page_count=2,
            citations=["WAIVER_SUBROGATION"]
        )
        
        # Create Guard handshake
        guard_handshake = create_guard_handshake(
            decision_proof_hash=guard_proof.proof_hash,
            project_id=brooklyn_opportunity.to_project_id(),
            status="REJECTED",
            parent_handshake=scout_handshake
        )
        
        assert guard_handshake.source_agent == AgentRole.GUARD
        assert guard_handshake.parent_handshake_id == scout_handshake.decision_hash
        assert guard_handshake.target_agent == AgentRole.FIXER or guard_handshake.target_agent is None
        
        print("\n✅ STEP 2: Guard rejected COI")
        print(f"   Status: {compliance_result.status}")
        print(f"   Deficiency: {compliance_result.deficiency_list[0]}")
        print(f"   Confidence: {compliance_result.confidence_score:.1%}")
        
        # STEP 3: Fixer drafts remediation email
        # Create deficiency report
        deficiency_report = DeficiencyReport(
            document_id=guard_doc_id,
            contractor_name=brooklyn_opportunity.owner_name,
            broker_name="Empire State Insurance Agency",
            broker_email="broker@empireinsurance.com",
            deficiencies=compliance_result.deficiency_list,
            citations=compliance_result.citations,
            project_id=brooklyn_opportunity.to_project_id(),
            permit_number=brooklyn_opportunity.permit_number,
            project_address=brooklyn_opportunity.address,
            validation_date=datetime.utcnow(),
            severity="HIGH"
        )
        
        # Create broker metadata
        broker_metadata = BrokerMetadata(
            broker_name="Empire State Insurance Agency",
            contact_name="John Smith",
            email="broker@empireinsurance.com",
            phone="2125551234"
        )
        
        # Create Fixer agent and generate remediation draft
        fixer_agent = OutreachAgent(base_upload_url="https://concomplai.com/upload")
        fixer_result = fixer_agent.generate_remediation_draft(
            deficiency_report=deficiency_report,
            broker_metadata=broker_metadata,
            parent_handshake=guard_handshake
        )
        
        # Verify Fixer output
        assert "email_draft" in fixer_result
        assert "audit_proof" in fixer_result
        assert "handshake" in fixer_result
        
        email_draft = fixer_result["email_draft"]
        fixer_handshake = fixer_result["handshake"]
        audit_proof = fixer_result["audit_proof"]
        
        # Verify email content
        assert isinstance(email_draft, EmailDraft)
        assert email_draft.tone == "Senior NYC Subcontractor"
        assert "Brooklyn Electrical Contractors" in email_draft.subject
        assert "420241234" in email_draft.subject  # DOB Job Number
        assert "DOB Job #420241234" in email_draft.body  # Job number in body
        assert "Waiver of Subrogation" in email_draft.body
        assert email_draft.correction_link
        
        # Verify tone is direct, not robotic
        assert "We're reviewing" in email_draft.body or "reviewing" in email_draft.body.lower()
        assert "need you to update" in email_draft.body or "Items to Fix" in email_draft.body
        # Should NOT have overly formal AI language
        assert "pursuant to" not in email_draft.body.lower()
        assert "herewith" not in email_draft.body.lower()
        
        # Verify handshake linkage
        assert fixer_handshake.source_agent == AgentRole.FIXER
        assert fixer_handshake.parent_handshake_id == guard_handshake.decision_hash
        
        # Verify AuditProof for Veteran Dashboard
        assert isinstance(audit_proof, DecisionProof)
        assert audit_proof.agent_name == "Fixer"
        assert audit_proof.decision == "REMEDIATION_DRAFTED"
        assert audit_proof.proof_hash  # Cryptographic hash present
        
        print("\n✅ STEP 3: Fixer drafted remediation email")
        print(f"   Tone: {email_draft.tone}")
        print(f"   Subject: {email_draft.subject}")
        print(f"   Body includes DOB Job #: {'Yes' if '420241234' in email_draft.body else 'No'}")
        print(f"   Correction link: {email_draft.correction_link}")
        
        # STEP 4: Verify complete audit chain
        audit_chain = AuditChain(
            project_id=brooklyn_opportunity.to_project_id(),
            chain_links=[scout_handshake, guard_handshake, fixer_handshake],
            total_cost_usd=scout_proof.cost_usd + guard_proof.cost_usd + fixer_result["cost_usd"],
            processing_time_seconds=1.5,
            outcome="PENDING_FIX"
        )
        
        # Verify chain integrity
        chain_valid = audit_chain.verify_chain_integrity()
        assert chain_valid is True, "Cryptographic hash chain must be valid"
        
        # Verify all three links
        assert len(audit_chain.chain_links) == 3
        assert audit_chain.chain_links[0].source_agent == AgentRole.SCOUT
        assert audit_chain.chain_links[1].source_agent == AgentRole.GUARD
        assert audit_chain.chain_links[2].source_agent == AgentRole.FIXER
        
        # Verify parent-child relationships
        assert audit_chain.chain_links[1].parent_handshake_id == audit_chain.chain_links[0].decision_hash
        assert audit_chain.chain_links[2].parent_handshake_id == audit_chain.chain_links[1].decision_hash
        
        print("\n✅ STEP 4: Audit chain verified")
        print(f"   Chain links: {len(audit_chain.chain_links)}")
        print(f"   Integrity: {'✅ VALID' if chain_valid else '❌ BROKEN'}")
        print(f"   Total cost: ${audit_chain.total_cost_usd:.6f}")
        
        # STEP 5: Verify cost efficiency
        target_cost = 0.005
        assert audit_chain.total_cost_usd < target_cost, \
            f"Pipeline cost ${audit_chain.total_cost_usd:.6f} must be < ${target_cost:.6f}"
        
        print(f"   Cost target: ${target_cost:.6f}")
        print(f"   Status: {'✅ UNDER TARGET' if audit_chain.total_cost_usd < target_cost else '❌ OVER TARGET'}")
        
        # Print full summary
        print("\n" + "=" * 80)
        print("BROOKLYN ELECTRICAL PERMIT - TRIPLE HANDSHAKE COMPLETE")
        print("=" * 80)
        print(audit_chain.to_summary())
        print("\nEMAIL PREVIEW:")
        print("-" * 80)
        print(f"To: {broker_metadata.contact_name} <{broker_metadata.email}>")
        print(f"Subject: {email_draft.subject}")
        print("\n" + email_draft.body[:500] + "...")
        print("-" * 80)
        print("=" * 80)
    
    def test_fixer_includes_dob_job_number(self):
        """Verify Fixer always includes NYC DOB Job Number in email"""
        deficiency_report = DeficiencyReport(
            document_id="TEST-DOC-001",
            contractor_name="Test Contractor LLC",
            deficiencies=["Missing coverage"],
            citations=["ISO_GL_MINIMUM"],
            project_id="TEST-PROJECT-123",
            permit_number="121234567",  # NYC DOB Job Number
            project_address="123 Test St, Brooklyn",
            severity="MEDIUM"
        )
        
        broker_metadata = BrokerMetadata(
            broker_name="Test Insurance Agency",
            contact_name="Jane Broker",
            email="jane@testinsurance.com"
        )
        
        fixer_agent = OutreachAgent()
        result = fixer_agent.generate_remediation_draft(
            deficiency_report=deficiency_report,
            broker_metadata=broker_metadata
        )
        
        email_draft = result["email_draft"]
        
        # Verify DOB Job Number in subject
        assert "121234567" in email_draft.subject
        
        # Verify DOB Job Number in body
        assert "DOB Job #121234567" in email_draft.body or "121234567" in email_draft.body
        
        print(f"\n✅ DOB Job Number included:")
        print(f"   Subject: {email_draft.subject}")
        print(f"   Body contains '121234567': Yes")
    
    def test_senior_subcontractor_tone(self):
        """Verify email uses Senior NYC Subcontractor tone, not robotic"""
        deficiency_report = DeficiencyReport(
            document_id="TONE-TEST-001",
            contractor_name="Brooklyn Builders Inc",
            deficiencies=["Additional Insured missing"],
            citations=["NYC_RCNY_101_08"],
            project_id="TONE-TEST",
            permit_number="999888777",
            severity="HIGH"
        )
        
        broker_metadata = BrokerMetadata(
            broker_name="NYC Insurance Partners",
            contact_name="Mike",
            email="mike@nycinsurance.com"
        )
        
        fixer_agent = OutreachAgent()
        result = fixer_agent.generate_remediation_draft(
            deficiency_report=deficiency_report,
            broker_metadata=broker_metadata
        )
        
        email_draft = result["email_draft"]
        body_lower = email_draft.body.lower()
        
        # Should have direct, human language
        assert "we're reviewing" in body_lower or "reviewing" in body_lower
        assert "need you" in body_lower or "items to fix" in body_lower
        
        # Should NOT have robotic/overly formal language
        assert "pursuant to" not in body_lower
        assert "herewith" not in body_lower
        assert "aforementioned" not in body_lower
        assert "kindly be informed" not in body_lower
        
        # Should have construction industry directness
        assert "upload" in body_lower or "send" in body_lower
        assert "48 hours" in body_lower or "timeline" in body_lower
        
        assert email_draft.tone == "Senior NYC Subcontractor"
        
        print(f"\n✅ Tone verification passed:")
        print(f"   Tone: {email_draft.tone}")
        print(f"   Direct language: Yes")
        print(f"   Non-robotic: Yes")
        print(f"   Construction industry voice: Yes")


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "-s"])
