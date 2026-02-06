"""
Governance Proof & Legal Sandbox - Task 4
Ensures no outreach email can be sent without governance approval.
Scans for Strict Liability triggers to protect the organization.
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum
import re


class LegalSandboxStatus(str, Enum):
    """Status of legal sandbox review"""
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    REQUIRES_COUNSEL = "REQUIRES_COUNSEL"


class StrictLiabilityTrigger(str, Enum):
    """
    Strict liability triggers that require legal review
    Based on construction insurance and tort law
    """
    GUARANTEE_LANGUAGE = "GUARANTEE_LANGUAGE"  # "We guarantee", "100% certain"
    ABSOLUTE_PROMISE = "ABSOLUTE_PROMISE"  # "Will definitely", "No chance of"
    WAIVER_OF_RIGHTS = "WAIVER_OF_RIGHTS"  # Waiving legal rights
    INDEMNIFICATION = "INDEMNIFICATION"  # Hold harmless language
    MISREPRESENTATION = "MISREPRESENTATION"  # False claims
    UNAUTHORIZED_PRACTICE = "UNAUTHORIZED_PRACTICE"  # Legal/insurance advice
    REGULATORY_VIOLATION = "REGULATORY_VIOLATION"  # Violates NYC codes
    HARASSMENT = "HARASSMENT"  # Aggressive language
    DISCRIMINATION = "DISCRIMINATION"  # Protected class references


class TriggerMatch(BaseModel):
    """Detected trigger in content"""
    trigger_type: StrictLiabilityTrigger
    matched_text: str
    location: str  # e.g., "subject_line", "body_paragraph_2"
    severity: str = Field(description="critical|high|moderate")
    explanation: str


class GovernanceProof(BaseModel):
    """
    Governance approval proof for outreach communications
    Required before any email can be sent by Fixer agent
    """
    proof_id: str
    timestamp: datetime = Field(default_factory=datetime.now)
    
    # Content being reviewed
    content_type: str = Field(description="endorsement_request|outreach_email|notification")
    subject_line: str
    body_text: str
    recipient_email: str
    
    # Legal sandbox scan results
    sandbox_status: LegalSandboxStatus
    triggers_detected: List[TriggerMatch] = Field(default_factory=list)
    risk_score: float = Field(ge=0.0, le=10.0, description="0=safe, 10=critical")
    
    # Approvals
    auto_approved: bool = Field(default=False)
    requires_human_review: bool = Field(default=False)
    reviewed_by: Optional[str] = None
    review_timestamp: Optional[datetime] = None
    review_notes: Optional[str] = None
    
    # NYC Code citations
    nyc_code_compliance: List[str] = Field(
        default_factory=list,
        description="NYC codes verified (e.g., 'RCNY §101-08')"
    )
    
    # Immutable hash for audit trail
    content_hash: str = Field(description="SHA-256 hash of content")
    
    # Block sending flag
    send_blocked: bool = Field(
        default=False,
        description="If True, email cannot be sent"
    )
    block_reason: Optional[str] = None
    
    class Config:
        frozen = False  # Allow status updates


class LegalSandbox:
    """
    Legal Sandbox Scanner for Fixer (Outreach Agent)
    Scans all outreach communications for strict liability triggers
    """
    
    # Regex patterns for strict liability triggers
    TRIGGER_PATTERNS = {
        StrictLiabilityTrigger.GUARANTEE_LANGUAGE: [
            r'\bguarantee\b',
            r'\b100%\s*(certain|sure|guaranteed)\b',
            r'\babsolutely\s*(certain|sure)\b',
            r'\bno\s*risk\b',
            r'\brisk[\-\s]free\b'
        ],
        StrictLiabilityTrigger.ABSOLUTE_PROMISE: [
            r'\bwill\s*definitely\b',
            r'\bno\s*chance\s*of\b',
            r'\bcannot\s*fail\b',
            r'\bimpossible\s*to\s*fail\b',
            r'\balways\s*works?\b'
        ],
        StrictLiabilityTrigger.WAIVER_OF_RIGHTS: [
            r'\bwaive\s*(all|any)?\s*rights?\b',
            r'\brelinquish\s*rights?\b',
            r'\bgive\s*up\s*(any|all)?\s*claims?\b'
        ],
        StrictLiabilityTrigger.INDEMNIFICATION: [
            r'\bhold\s*harmless\b',
            r'\bindemnify\b',
            r'\bindemnification\b',
            r'\bdefend\s*and\s*hold\b'
        ],
        StrictLiabilityTrigger.UNAUTHORIZED_PRACTICE: [
            r'\blegal\s*advice\b',
            r'\bas\s*your\s*attorney\b',
            r'\bwe\s*recommend\s*filing\b',
            r'\binsurance\s*advice\b',
            r'\byou\s*should\s*purchase\b'
        ],
        StrictLiabilityTrigger.HARASSMENT: [
            r'\bfinal\s*warning\b',
            r'\bimmediate\s*legal\s*action\b',
            r'\bwill\s*sue\b',
            r'\btake\s*legal\s*action\b'
        ],
        StrictLiabilityTrigger.DISCRIMINATION: [
            r'\b(age|race|gender|religion|national\s*origin)\b.*\b(because|due\s*to)\b',
            r'\bprotected\s*class\b'
        ]
    }
    
    def __init__(self):
        self.proofs: List[GovernanceProof] = []
    
    def scan_content(
        self,
        proof_id: str,
        content_type: str,
        subject_line: str,
        body_text: str,
        recipient_email: str,
        nyc_codes: Optional[List[str]] = None
    ) -> GovernanceProof:
        """
        Scan content for strict liability triggers
        Returns GovernanceProof with approval/rejection decision
        """
        import hashlib
        
        # Compute content hash
        content = f"{subject_line}\n{body_text}"
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        
        # Scan for triggers
        triggers = []
        combined_text = f"{subject_line}\n{body_text}".lower()
        
        for trigger_type, patterns in self.TRIGGER_PATTERNS.items():
            for pattern in patterns:
                matches = re.finditer(pattern, combined_text, re.IGNORECASE)
                for match in matches:
                    # Determine location
                    if match.start() < len(subject_line):
                        location = "subject_line"
                    else:
                        location = "body_text"
                    
                    # Determine severity
                    severity = self._get_trigger_severity(trigger_type)
                    
                    triggers.append(TriggerMatch(
                        trigger_type=trigger_type,
                        matched_text=match.group(0),
                        location=location,
                        severity=severity,
                        explanation=self._get_trigger_explanation(trigger_type)
                    ))
        
        # Calculate risk score (0-10)
        risk_score = self._calculate_risk_score(triggers)
        
        # Determine sandbox status
        if risk_score >= 8.0:
            status = LegalSandboxStatus.REQUIRES_COUNSEL
            send_blocked = True
            block_reason = "Critical risk - legal counsel required"
        elif risk_score >= 5.0:
            status = LegalSandboxStatus.PENDING
            send_blocked = True
            block_reason = "High risk - human review required"
        elif len(triggers) > 0:
            status = LegalSandboxStatus.PENDING
            send_blocked = True
            block_reason = "Triggers detected - review required"
        else:
            status = LegalSandboxStatus.APPROVED
            send_blocked = False
        
        # Create governance proof
        proof = GovernanceProof(
            proof_id=proof_id,
            content_type=content_type,
            subject_line=subject_line,
            body_text=body_text,
            recipient_email=recipient_email,
            sandbox_status=status,
            triggers_detected=triggers,
            risk_score=risk_score,
            auto_approved=(status == LegalSandboxStatus.APPROVED),
            requires_human_review=(status != LegalSandboxStatus.APPROVED),
            nyc_code_compliance=nyc_codes or [],
            content_hash=content_hash,
            send_blocked=send_blocked,
            block_reason=block_reason
        )
        
        self.proofs.append(proof)
        return proof
    
    def approve_proof(
        self,
        proof_id: str,
        reviewer_id: str,
        notes: Optional[str] = None
    ) -> bool:
        """Human approval of a governance proof"""
        for proof in self.proofs:
            if proof.proof_id == proof_id:
                proof.sandbox_status = LegalSandboxStatus.APPROVED
                proof.reviewed_by = reviewer_id
                proof.review_timestamp = datetime.now()
                proof.review_notes = notes
                proof.send_blocked = False
                proof.block_reason = None
                return True
        return False
    
    def reject_proof(
        self,
        proof_id: str,
        reviewer_id: str,
        reason: str
    ) -> bool:
        """Human rejection of a governance proof"""
        for proof in self.proofs:
            if proof.proof_id == proof_id:
                proof.sandbox_status = LegalSandboxStatus.REJECTED
                proof.reviewed_by = reviewer_id
                proof.review_timestamp = datetime.now()
                proof.review_notes = reason
                proof.send_blocked = True
                proof.block_reason = reason
                return True
        return False
    
    def _get_trigger_severity(self, trigger_type: StrictLiabilityTrigger) -> str:
        """Determine severity of trigger"""
        critical_triggers = [
            StrictLiabilityTrigger.INDEMNIFICATION,
            StrictLiabilityTrigger.WAIVER_OF_RIGHTS,
            StrictLiabilityTrigger.UNAUTHORIZED_PRACTICE
        ]
        
        high_triggers = [
            StrictLiabilityTrigger.GUARANTEE_LANGUAGE,
            StrictLiabilityTrigger.ABSOLUTE_PROMISE,
            StrictLiabilityTrigger.HARASSMENT,
            StrictLiabilityTrigger.DISCRIMINATION
        ]
        
        if trigger_type in critical_triggers:
            return "critical"
        elif trigger_type in high_triggers:
            return "high"
        else:
            return "moderate"
    
    def _get_trigger_explanation(self, trigger_type: StrictLiabilityTrigger) -> str:
        """Get explanation for trigger"""
        explanations = {
            StrictLiabilityTrigger.GUARANTEE_LANGUAGE: "Guarantee language creates strict liability exposure",
            StrictLiabilityTrigger.ABSOLUTE_PROMISE: "Absolute promises may constitute warranties",
            StrictLiabilityTrigger.WAIVER_OF_RIGHTS: "Waiving rights may be unenforceable or create liability",
            StrictLiabilityTrigger.INDEMNIFICATION: "Hold harmless language requires legal review",
            StrictLiabilityTrigger.UNAUTHORIZED_PRACTICE: "Providing legal/insurance advice without license",
            StrictLiabilityTrigger.HARASSMENT: "Threatening language may constitute harassment",
            StrictLiabilityTrigger.DISCRIMINATION: "References to protected classes require review"
        }
        return explanations.get(trigger_type, "Requires legal review")
    
    def _calculate_risk_score(self, triggers: List[TriggerMatch]) -> float:
        """Calculate risk score from 0-10"""
        if not triggers:
            return 0.0
        
        severity_scores = {
            'critical': 4.0,
            'high': 2.0,
            'moderate': 1.0
        }
        
        score = sum(severity_scores.get(t.severity, 0) for t in triggers)
        return min(score, 10.0)  # Cap at 10
    
    def get_pending_reviews(self) -> List[GovernanceProof]:
        """Get all proofs awaiting review"""
        return [
            p for p in self.proofs
            if p.sandbox_status == LegalSandboxStatus.PENDING
            or p.sandbox_status == LegalSandboxStatus.REQUIRES_COUNSEL
        ]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get sandbox statistics"""
        total = len(self.proofs)
        if total == 0:
            return {'total_proofs': 0}
        
        approved = len([p for p in self.proofs if p.sandbox_status == LegalSandboxStatus.APPROVED])
        rejected = len([p for p in self.proofs if p.sandbox_status == LegalSandboxStatus.REJECTED])
        pending = len([p for p in self.proofs if p.sandbox_status == LegalSandboxStatus.PENDING])
        
        return {
            'total_proofs': total,
            'approved': approved,
            'rejected': rejected,
            'pending': pending,
            'requires_counsel': len([p for p in self.proofs if p.sandbox_status == LegalSandboxStatus.REQUIRES_COUNSEL]),
            'auto_approval_rate': len([p for p in self.proofs if p.auto_approved]) / total * 100,
            'avg_risk_score': sum(p.risk_score for p in self.proofs) / total
        }


# Global singleton
_legal_sandbox: Optional[LegalSandbox] = None


def get_legal_sandbox() -> LegalSandbox:
    """Get or create global legal sandbox instance"""
    global _legal_sandbox
    if _legal_sandbox is None:
        _legal_sandbox = LegalSandbox()
    return _legal_sandbox
