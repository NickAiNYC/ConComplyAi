"""
Enhanced Agent Handshake Protocol - Multi-Agent Integration
Extends existing schemas with Scout/Guard/Watchman/Fixer coordination
"""
from typing import Literal, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class AgentRole(str, Enum):
    """Agent types in the ConComplyAi platform"""
    SCOUT = "Scout"              # Opportunity discovery
    GUARD = "Guard"              # Compliance validation
    WATCHMAN = "Watchman"        # Site monitoring
    FIXER = "Fixer"              # Autonomous remediation
    INTELLIGENCE = "Intelligence"  # Geospatial/data layer


class AgentHandshakeV2(BaseModel):
    """
    Enhanced agent handshake for cryptographic audit chains.
    Links agent decisions into an immutable audit trail.
    Required for NYC Local Law 144 compliance.
    
    Each agent output generates a handshake that:
    1. Links to parent decision via SHA-256 hash
    2. Specifies next agent in the chain
    3. Creates tamper-proof audit trail
    """
    # Identity
    source_agent: AgentRole = Field(description="Agent generating this handshake")
    target_agent: Optional[AgentRole] = Field(
        default=None,
        description="Next agent in chain (None if terminal)"
    )
    
    # Project context
    project_id: str = Field(description="Unique project/opportunity identifier")
    
    # Audit chain
    decision_hash: str = Field(
        description="SHA-256 hash from DecisionProof linking to this handshake"
    )
    parent_handshake_id: Optional[str] = Field(
        default=None,
        description="Links to previous agent's decision_hash (creates chain)"
    )
    
    # Metadata
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    transition_reason: str = Field(
        description="Why this handoff occurred (e.g., 'deficiency_found', 'approved')"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context for handoff"
    )
    
    class Config:
        frozen = True  # Immutable for audit integrity
    
    def to_dict(self) -> Dict[str, Any]:
        """Export to dict for hashing"""
        return {
            "source_agent": self.source_agent.value,
            "target_agent": self.target_agent.value if self.target_agent else None,
            "project_id": self.project_id,
            "decision_hash": self.decision_hash,
            "parent_handshake_id": self.parent_handshake_id,
            "timestamp": self.timestamp.isoformat(),
            "transition_reason": self.transition_reason,
        }


class AgentOutputProtocol(BaseModel):
    """
    Base class all agent outputs inherit from.
    Ensures consistent interface across Scout, Guard, Watchman, Fixer.
    """
    handshake: AgentHandshakeV2
    decision_proof_hash: str = Field(description="SHA-256 hash of DecisionProof")
    processing_cost_usd: float = Field(ge=0.0, description="USD cost of this operation")
    confidence_score: float = Field(ge=0.0, le=1.0, description="AI confidence")
    agent_name: AgentRole
    
    class Config:
        frozen = True


class AuditChain(BaseModel):
    """
    Complete audit chain from Scout discovery to final outcome.
    Used for investor demos and regulatory compliance.
    """
    project_id: str
    chain_links: list[AgentHandshakeV2] = Field(default_factory=list)
    total_cost_usd: float = 0.0
    processing_time_seconds: float = 0.0
    outcome: Literal["BID_READY", "PENDING_FIX", "REJECTED", "MONITORING_ACTIVE"]
    
    def verify_chain_integrity(self) -> bool:
        """
        Verify that each link properly chains to the previous one.
        Returns True if all parent_handshake_id values match decision_hash of previous link.
        """
        if len(self.chain_links) <= 1:
            return True
        
        for i in range(1, len(self.chain_links)):
            current = self.chain_links[i]
            previous = self.chain_links[i-1]
            
            if current.parent_handshake_id != previous.decision_hash:
                return False
        
        return True
    
    def to_summary(self) -> str:
        """Generate human-readable audit chain summary"""
        lines = [
            f"Audit Chain for Project: {self.project_id}",
            f"Total Cost: ${self.total_cost_usd:.4f}",
            f"Processing Time: {self.processing_time_seconds:.2f}s",
            f"Final Outcome: {self.outcome}",
            "",
            "Chain Links:"
        ]
        
        for i, link in enumerate(self.chain_links, 1):
            lines.append(
                f"  {i}. {link.source_agent.value} → {link.target_agent.value if link.target_agent else 'TERMINAL'}"
            )
            lines.append(f"     Hash: {link.decision_hash[:16]}...")
            lines.append(f"     Reason: {link.transition_reason}")
        
        chain_valid = self.verify_chain_integrity()
        lines.append(f"\nChain Integrity: {'✅ VALID' if chain_valid else '❌ BROKEN'}")
        
        return "\n".join(lines)


# Integration helpers for existing Guard agent
def create_guard_handshake(
    decision_proof_hash: str,
    project_id: str,
    status: Literal["APPROVED", "REJECTED", "ILLEGIBLE", "PENDING_FIX"],
    parent_handshake: Optional[AgentHandshakeV2] = None
) -> AgentHandshakeV2:
    """
    Helper to create Guard agent handshake compatible with existing implementation.
    
    Maps Guard validation status to appropriate target agent:
    - APPROVED → Watchman (for site monitoring)
    - PENDING_FIX → Fixer (for remediation)
    - REJECTED → None (terminal)
    - ILLEGIBLE → None (terminal, needs manual review)
    """
    # Determine target agent based on validation result
    target_agent = None
    transition_reason = status
    
    if status == "APPROVED":
        target_agent = AgentRole.WATCHMAN
        transition_reason = "compliance_approved"
    elif status == "PENDING_FIX":
        target_agent = AgentRole.FIXER
        transition_reason = "deficiency_found"
    elif status == "REJECTED":
        transition_reason = "compliance_failed"
    elif status == "ILLEGIBLE":
        transition_reason = "manual_review_required"
    
    return AgentHandshakeV2(
        source_agent=AgentRole.GUARD,
        target_agent=target_agent,
        project_id=project_id,
        decision_hash=decision_proof_hash,
        parent_handshake_id=parent_handshake.decision_hash if parent_handshake else None,
        transition_reason=transition_reason
    )
