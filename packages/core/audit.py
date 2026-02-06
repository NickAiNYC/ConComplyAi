"""
DecisionProof Engine - Cryptographic Audit Trail for AI Decisions
Implements SHA-256 hashing with logic citations for regulatory compliance
Satisfies NYC Local Law 144 and EU AI Act Article 13 requirements
"""
import hashlib
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum


class ComplianceStandard(str, Enum):
    """Regulatory standards for construction compliance"""
    NYC_RCNY_101_08 = "NYC_RCNY_101_08"  # NYC Additional Insured requirements
    OSHA_1926_501 = "OSHA_1926_501"      # Fall Protection
    NYC_BC_3301 = "NYC_BC_3301"          # Building Code - Construction Safety
    OSHA_1910_134 = "OSHA_1910_134"      # Respiratory Protection
    NYC_LL_196 = "NYC_LL_196"            # Site Safety Training
    ISO_GL_MINIMUM = "ISO_GL_MINIMUM"    # General Liability $2M/$4M minimum
    WAIVER_SUBROGATION = "WAIVER_SUBROGATION"  # Insurance waiver requirement
    PER_PROJECT_AGGREGATE = "PER_PROJECT_AGGREGATE"  # Separate aggregate per project


class LogicCitation(BaseModel):
    """Single logic citation explaining why a decision was made"""
    standard: ComplianceStandard
    clause: str = Field(description="Specific clause or section number")
    interpretation: str = Field(description="Human-readable interpretation")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in this citation")
    
    def to_text(self) -> str:
        """Format citation as readable text"""
        return f"{self.standard.value} § {self.clause}: {self.interpretation} (confidence: {self.confidence:.2f})"


class DecisionProof(BaseModel):
    """
    Cryptographic proof of an AI decision with full audit trail
    Immutable record for compliance and legal defense
    """
    decision_id: str = Field(description="Unique identifier for this decision")
    timestamp: datetime = Field(default_factory=datetime.now)
    agent_name: str = Field(description="Agent that made the decision")
    
    # Input context
    input_data: Dict[str, Any] = Field(description="Input data that led to decision")
    
    # Decision output
    decision: str = Field(description="The actual decision made (PASS/FAIL/PENDING)")
    confidence: float = Field(ge=0.0, le=1.0, description="Overall confidence score")
    
    # Explainability - The KEY to NYC Local Law 144 compliance
    logic_citations: List[LogicCitation] = Field(
        default_factory=list,
        description="Citations to regulations that justify this decision"
    )
    reasoning: str = Field(description="Human-readable explanation of decision")
    
    # Risk assessment
    risk_level: str = Field(description="CRITICAL/HIGH/MEDIUM/LOW")
    estimated_financial_impact: Optional[float] = Field(
        default=None,
        description="Estimated cost/savings in USD"
    )
    
    # Cost tracking
    cost_usd: float = Field(default=0.0, description="Cost of making this decision")
    
    # Cryptographic proof - SHA-256 hash of decision
    proof_hash: str = Field(default="", description="SHA-256 hash for tamper detection")
    
    class Config:
        arbitrary_types_allowed = True
    
    def generate_hash(self) -> str:
        """
        Generate SHA-256 hash of the decision for tamper-proof audit trail
        
        Hash includes:
        - Decision ID
        - Timestamp
        - Agent name
        - Input data (serialized)
        - Decision output
        - All logic citations
        
        Returns:
            64-character hex SHA-256 hash
        """
        # Create canonical representation for hashing
        hash_input = {
            "decision_id": self.decision_id,
            "timestamp": self.timestamp.isoformat(),
            "agent_name": self.agent_name,
            "input_data": self._serialize_for_hash(self.input_data),
            "decision": self.decision,
            "confidence": self.confidence,
            "logic_citations": [
                {
                    "standard": c.standard.value,
                    "clause": c.clause,
                    "interpretation": c.interpretation,
                    "confidence": c.confidence
                }
                for c in self.logic_citations
            ],
            "reasoning": self.reasoning,
            "risk_level": self.risk_level,
        }
        
        # Convert to deterministic JSON string (sorted keys)
        json_str = json.dumps(hash_input, sort_keys=True, separators=(',', ':'))
        
        # Generate SHA-256 hash
        hash_obj = hashlib.sha256(json_str.encode('utf-8'))
        return hash_obj.hexdigest()
    
    def _serialize_for_hash(self, data: Any) -> Any:
        """
        Recursively serialize data for consistent hashing
        Handles special types like datetime, BaseModel, etc.
        """
        if isinstance(data, dict):
            return {k: self._serialize_for_hash(v) for k, v in sorted(data.items())}
        elif isinstance(data, (list, tuple)):
            return [self._serialize_for_hash(item) for item in data]
        elif isinstance(data, datetime):
            return data.isoformat()
        elif isinstance(data, BaseModel):
            return self._serialize_for_hash(data.dict())
        elif hasattr(data, '__dict__'):
            return self._serialize_for_hash(data.__dict__)
        else:
            return data
    
    def verify_hash(self) -> bool:
        """
        Verify that the stored hash matches the current decision state
        
        Returns:
            True if hash is valid (not tampered), False if tampered
        """
        if not self.proof_hash:
            return False
        
        current_hash = self.generate_hash()
        return current_hash == self.proof_hash
    
    def finalize(self) -> 'DecisionProof':
        """
        Finalize the decision proof by generating and storing the hash
        Should be called after all decision data is populated
        
        Returns:
            Self (for method chaining)
        """
        self.proof_hash = self.generate_hash()
        return self
    
    def to_audit_report(self) -> str:
        """
        Generate human-readable audit report for this decision
        Suitable for presenting to regulators or legal teams
        """
        report_lines = [
            "=" * 80,
            f"DECISION AUDIT REPORT",
            "=" * 80,
            f"Decision ID: {self.decision_id}",
            f"Timestamp: {self.timestamp.isoformat()}",
            f"Agent: {self.agent_name}",
            f"Decision: {self.decision}",
            f"Confidence: {self.confidence:.2%}",
            f"Risk Level: {self.risk_level}",
            "",
            "REASONING:",
            self.reasoning,
            "",
            "REGULATORY COMPLIANCE CITATIONS:",
        ]
        
        if not self.logic_citations:
            report_lines.append("  (No citations provided)")
        else:
            for i, citation in enumerate(self.logic_citations, 1):
                report_lines.append(f"  {i}. {citation.to_text()}")
        
        report_lines.extend([
            "",
            f"FINANCIAL IMPACT: ${self.estimated_financial_impact:,.2f}" if self.estimated_financial_impact else "FINANCIAL IMPACT: Not calculated",
            f"PROCESSING COST: ${self.cost_usd:.6f}",
            "",
            f"PROOF HASH (SHA-256): {self.proof_hash}",
            f"Hash Valid: {self.verify_hash()}",
            "=" * 80,
        ])
        
        return "\n".join(report_lines)


def create_decision_proof(
    agent_name: str,
    decision: str,
    input_data: Dict[str, Any],
    logic_citations: List[LogicCitation],
    reasoning: str,
    confidence: float = 1.0,
    risk_level: str = "MEDIUM",
    estimated_financial_impact: Optional[float] = None,
    cost_usd: float = 0.0
) -> DecisionProof:
    """
    Factory function to create a finalized DecisionProof
    
    Args:
        agent_name: Name of the agent making the decision
        decision: The decision made (e.g., "PASS", "FAIL", "PENDING_REVIEW")
        input_data: Input data that led to the decision
        logic_citations: List of regulatory citations justifying the decision
        reasoning: Human-readable explanation
        confidence: Confidence score 0.0-1.0
        risk_level: Risk classification
        estimated_financial_impact: Financial impact in USD
        cost_usd: Cost of making this decision
    
    Returns:
        Finalized DecisionProof with SHA-256 hash
    """
    # Generate unique decision ID
    timestamp = datetime.now()
    decision_id = f"{agent_name}-{timestamp.strftime('%Y%m%d%H%M%S')}-{hash(str(input_data)) % 10000:04d}"
    
    # Create proof object
    proof = DecisionProof(
        decision_id=decision_id,
        timestamp=timestamp,
        agent_name=agent_name,
        input_data=input_data,
        decision=decision,
        confidence=confidence,
        logic_citations=logic_citations,
        reasoning=reasoning,
        risk_level=risk_level,
        estimated_financial_impact=estimated_financial_impact,
        cost_usd=cost_usd
    )
    
    # Finalize with hash
    return proof.finalize()


def validate_decision_proof(proof: DecisionProof) -> Dict[str, Any]:
    """
    Validate a DecisionProof for compliance and integrity
    
    Returns:
        Dict with validation results and any issues found
    """
    issues = []
    
    # Check hash integrity
    if not proof.verify_hash():
        issues.append("CRITICAL: Hash verification failed - proof may be tampered")
    
    # Check required fields
    if not proof.logic_citations:
        issues.append("WARNING: No logic citations provided - fails NYC Local Law 144")
    
    if proof.confidence < 0.5:
        issues.append(f"WARNING: Low confidence ({proof.confidence:.2%}) - consider human review")
    
    if not proof.reasoning or len(proof.reasoning) < 10:
        issues.append("WARNING: Insufficient reasoning provided")
    
    # Check timestamp is not in future
    if proof.timestamp > datetime.now():
        issues.append("ERROR: Timestamp is in the future - invalid proof")
    
    return {
        "valid": len([i for i in issues if i.startswith("CRITICAL") or i.startswith("ERROR")]) == 0,
        "issues": issues,
        "hash_valid": proof.verify_hash(),
        "has_citations": len(proof.logic_citations) > 0,
        "confidence_adequate": proof.confidence >= 0.5
    }
