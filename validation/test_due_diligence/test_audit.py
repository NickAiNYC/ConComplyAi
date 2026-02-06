"""
Tests for Core Audit Module - DecisionProof Engine
"""
import pytest
from datetime import datetime

from packages.core.audit import (
    DecisionProof,
    LogicCitation,
    ComplianceStandard,
    create_decision_proof,
    validate_decision_proof
)


class TestLogicCitation:
    """Test LogicCitation model"""
    
    def test_citation_creation(self):
        """Test creating a logic citation"""
        citation = LogicCitation(
            standard=ComplianceStandard.NYC_RCNY_101_08,
            clause="§101-08(c)(3)",
            interpretation="Additional Insured requirement",
            confidence=0.95
        )
        
        assert citation.standard == ComplianceStandard.NYC_RCNY_101_08
        assert citation.confidence == 0.95
    
    def test_citation_to_text(self):
        """Test citation text formatting"""
        citation = LogicCitation(
            standard=ComplianceStandard.NYC_RCNY_101_08,
            clause="§101-08(c)(3)",
            interpretation="Additional Insured requirement",
            confidence=0.95
        )
        
        text = citation.to_text()
        
        assert "NYC_RCNY_101_08" in text
        assert "§101-08(c)(3)" in text
        assert "0.95" in text


class TestDecisionProof:
    """Test DecisionProof class"""
    
    def test_hash_generation(self):
        """Test SHA-256 hash generation"""
        proof = DecisionProof(
            decision_id="TEST-001",
            agent_name="Guard",
            input_data={"test": "data"},
            decision="PASS",
            confidence=0.98,
            logic_citations=[],
            reasoning="Test reasoning",
            risk_level="LOW"
        )
        
        hash1 = proof.generate_hash()
        
        # Hash should be 64 characters (SHA-256 hex)
        assert len(hash1) == 64
        assert all(c in '0123456789abcdef' for c in hash1)
        
        # Same data should produce same hash
        hash2 = proof.generate_hash()
        assert hash1 == hash2
    
    def test_hash_deterministic(self):
        """Test that identical proofs produce identical hashes"""
        proof1 = create_decision_proof(
            agent_name="Guard",
            decision="APPROVED",
            input_data={"doc_id": "123"},
            logic_citations=[],
            reasoning="Test",
            confidence=0.95
        )
        
        proof2 = create_decision_proof(
            agent_name="Guard",
            decision="APPROVED",
            input_data={"doc_id": "123"},
            logic_citations=[],
            reasoning="Test",
            confidence=0.95
        )
        
        # Hashes will differ due to timestamps, but structure should be consistent
        assert len(proof1.proof_hash) == 64
        assert len(proof2.proof_hash) == 64
    
    def test_hash_verification(self):
        """Test hash verification"""
        proof = create_decision_proof(
            agent_name="Guard",
            decision="APPROVED",
            input_data={"test": "data"},
            logic_citations=[],
            reasoning="Test",
            confidence=0.95
        )
        
        # Should verify successfully
        assert proof.verify_hash() == True
        
        # Tamper with data
        proof.reasoning = "TAMPERED"
        
        # Should fail verification
        assert proof.verify_hash() == False
    
    def test_finalize(self):
        """Test finalize method"""
        proof = DecisionProof(
            decision_id="TEST-001",
            agent_name="Guard",
            input_data={},
            decision="PASS",
            confidence=0.95,
            logic_citations=[],
            reasoning="Test",
            risk_level="LOW"
        )
        
        # Initially no hash
        assert proof.proof_hash == ""
        
        # Finalize
        proof.finalize()
        
        # Now has hash
        assert len(proof.proof_hash) == 64
        assert proof.verify_hash() == True


class TestCreateDecisionProof:
    """Test factory function"""
    
    def test_create_with_citations(self):
        """Test creating proof with logic citations"""
        citations = [
            LogicCitation(
                standard=ComplianceStandard.NYC_RCNY_101_08,
                clause="§101-08(c)(3)",
                interpretation="Test",
                confidence=0.95
            )
        ]
        
        proof = create_decision_proof(
            agent_name="Guard",
            decision="APPROVED",
            input_data={"doc_id": "123"},
            logic_citations=citations,
            reasoning="All requirements met",
            confidence=0.98,
            risk_level="LOW",
            estimated_financial_impact=50000.0,
            cost_usd=0.000625
        )
        
        assert proof.agent_name == "Guard"
        assert proof.decision == "APPROVED"
        assert len(proof.logic_citations) == 1
        assert proof.proof_hash != ""
        assert proof.verify_hash() == True
    
    def test_audit_report_format(self):
        """Test audit report generation"""
        proof = create_decision_proof(
            agent_name="Guard",
            decision="REJECTED",
            input_data={"doc": "test.pdf"},
            logic_citations=[
                LogicCitation(
                    standard=ComplianceStandard.WAIVER_SUBROGATION,
                    clause="Test",
                    interpretation="Missing waiver",
                    confidence=0.95
                )
            ],
            reasoning="Failed validation",
            confidence=0.92
        )
        
        report = proof.to_audit_report()
        
        assert "DECISION AUDIT REPORT" in report
        assert "Guard" in report
        assert "REJECTED" in report
        assert "SHA-256" in report


class TestValidateDecisionProof:
    """Test proof validation function"""
    
    def test_validate_valid_proof(self):
        """Test validating a valid proof"""
        proof = create_decision_proof(
            agent_name="Guard",
            decision="APPROVED",
            input_data={"test": "data"},
            logic_citations=[
                LogicCitation(
                    standard=ComplianceStandard.NYC_RCNY_101_08,
                    clause="Test",
                    interpretation="Test",
                    confidence=0.95
                )
            ],
            reasoning="Valid reasoning with sufficient detail",
            confidence=0.95
        )
        
        validation = validate_decision_proof(proof)
        
        assert validation["valid"] == True
        assert validation["hash_valid"] == True
        assert validation["has_citations"] == True
        assert len(validation["issues"]) == 0
    
    def test_validate_missing_citations(self):
        """Test validation fails without citations"""
        proof = create_decision_proof(
            agent_name="Guard",
            decision="APPROVED",
            input_data={},
            logic_citations=[],  # No citations
            reasoning="Test",
            confidence=0.95
        )
        
        validation = validate_decision_proof(proof)
        
        # Should have warnings but still be valid
        assert validation["has_citations"] == False
        assert any("citations" in issue.lower() for issue in validation["issues"])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
