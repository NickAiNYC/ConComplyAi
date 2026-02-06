"""
Tests for Guard Agent Validator
"""
import pytest
from pathlib import Path

from packages.agents.guard.validator import validate_coi, ComplianceResult


class TestValidateCOI:
    """Test validate_coi function"""
    
    def test_compliant_document(self):
        """Test validation of compliant COI"""
        result_dict = validate_coi(Path("sample_data/coi_compliant.pdf"))
        result = result_dict["result"]
        
        assert isinstance(result, ComplianceResult)
        assert result.status == "APPROVED"
        assert result.confidence_score >= 0.95
        assert len(result.deficiency_list) == 0
        assert result.processing_cost > 0
        assert result.ocr_confidence >= 0.95
    
    def test_missing_waiver_document(self):
        """Test validation of COI missing waiver"""
        result_dict = validate_coi(Path("sample_data/coi_missing_waiver.pdf"))
        result = result_dict["result"]
        
        assert result.status == "REJECTED"
        assert len(result.deficiency_list) > 0
        assert any("Waiver" in d for d in result.deficiency_list)
        assert len(result.citations) > 0
        assert "NYC SCA Bulletin" in result.citations[0]
    
    def test_illegible_document(self):
        """Test validation of illegible document"""
        result_dict = validate_coi(Path("sample_data/coi_illegible.pdf"))
        result = result_dict["result"]
        
        assert result.status == "ILLEGIBLE"
        assert result.ocr_confidence < 0.95
        assert len(result.deficiency_list) > 0
        assert "OCR confidence" in result.deficiency_list[0]
    
    def test_returns_decision_proof(self):
        """Test that decision proof is included"""
        result_dict = validate_coi(Path("sample_data/coi_compliant.pdf"))
        
        assert "decision_proof_obj" in result_dict
        proof = result_dict["decision_proof_obj"]
        
        assert proof.agent_name == "Guard"
        assert proof.proof_hash != ""
        assert proof.verify_hash() == True
    
    def test_returns_token_usage(self):
        """Test that token usage is returned"""
        result_dict = validate_coi(Path("sample_data/coi_compliant.pdf"))
        
        assert "input_tokens" in result_dict
        assert "output_tokens" in result_dict
        assert result_dict["input_tokens"] > 0
        assert result_dict["output_tokens"] > 0
    
    def test_cost_within_target(self):
        """Test that cost stays under $0.007 target"""
        result_dict = validate_coi(Path("sample_data/coi_compliant.pdf"))
        result = result_dict["result"]
        
        # Should be under target with 10% margin
        assert result.processing_cost <= 0.010
        # Ideally under strict target
        assert result.processing_cost <= 0.007


class TestComplianceResult:
    """Test ComplianceResult model"""
    
    def test_frozen_model(self):
        """Test that ComplianceResult is immutable"""
        result = ComplianceResult(
            status="APPROVED",
            deficiency_list=[],
            decision_proof="test_hash",
            confidence_score=0.95,
            processing_cost=0.001,
            document_id="TEST-001",
            ocr_confidence=0.98,
            page_count=1,
            citations=[]
        )
        
        # Should not be able to modify
        with pytest.raises(Exception):  # Pydantic raises ValidationError
            result.status = "REJECTED"
    
    def test_required_fields(self):
        """Test that all required fields are present"""
        result = ComplianceResult(
            status="APPROVED",
            deficiency_list=[],
            decision_proof="abc123",
            confidence_score=0.95,
            processing_cost=0.001,
            document_id="TEST-001",
            ocr_confidence=0.98,
            page_count=1,
            citations=[]
        )
        
        assert result.status in ["APPROVED", "REJECTED", "ILLEGIBLE", "PENDING_FIX"]
        assert isinstance(result.deficiency_list, list)
        assert isinstance(result.citations, list)
        assert 0 <= result.confidence_score <= 1
        assert 0 <= result.ocr_confidence <= 1
        assert result.page_count >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
