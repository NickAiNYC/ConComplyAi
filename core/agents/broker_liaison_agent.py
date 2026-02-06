"""
BrokerLiaison Agent - Task 1: The Outreach Bridge

Drafts insurance endorsement requests to fix compliance gaps.
Triggered when user clicks 'Fix Compliance' on a ScopeSignal lead.

NYC 2027 COMPLIANCE: All outreach requires Legal Sandbox approval
- Scans for strict liability triggers
- Generates GovernanceProof before sending
- Blocks sending if triggers detected

Integrates with ConComply-Scope Suite 2027 standards.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
import hashlib

from packages.core import (
    ScopeSignal,
    EndorsementRequest,
    BrokerContact,
    AgencyRequirement,
    DecisionProof,
    AgentHandshake
)
from packages.monitoring import (
    get_legal_sandbox,
    GovernanceProof,
    LegalSandboxStatus
)


class BrokerLiaisonAgent:
    """
    Agent responsible for drafting endorsement requests to insurance brokers
    based on detected compliance gaps and agency requirements.
    
    NYC 2027: Integrates Legal Sandbox for liability protection
    """
    
    AGENT_ID = "BrokerLiaison-v2.1-LegalSandbox"
    
    # Agency-specific endorsement requirements
    AGENCY_ENDORSEMENTS = {
        AgencyRequirement.SCA: [
            "Additional Insured - Primary & Non-Contributory",
            "Waiver of Subrogation",
            "Per Project Aggregate",
            "Notice of Cancellation - 30 days",
            "Pollution Liability for Renovation Projects"
        ],
        AgencyRequirement.DDC: [
            "Additional Insured - Broad Form",
            "Waiver of Subrogation",
            "Per Project Aggregate",
            "Notice of Cancellation - 60 days",
            "Professional Liability (if design services)"
        ],
        AgencyRequirement.HPD: [
            "Additional Insured",
            "Waiver of Subrogation",
            "Lead-Based Paint Coverage",
            "Notice of Cancellation - 30 days"
        ],
        AgencyRequirement.DOT: [
            "Additional Insured",
            "Waiver of Subrogation",
            "Per Project Aggregate",
            "Highway Traffic Liability",
            "Notice of Cancellation - 30 days"
        ]
    }
    
    # Cost tracking for $0.007/doc efficiency
    TOKEN_COST_PER_1K = 0.002  # Estimate for Haiku model
    AVERAGE_TOKENS_PER_DRAFT = 350  # Conservative estimate
    
    def __init__(self):
        self.requests_drafted = 0
        self.total_cost = 0.0
    
    def draft_endorsement_request(
        self,
        signal: ScopeSignal,
        from_agent: str = "OpportunityAgent"
    ) -> EndorsementRequest:
        """
        Draft an endorsement request for a ScopeSignal lead.
        
        Args:
            signal: The ScopeSignal opportunity with compliance gaps
            from_agent: The agent that passed this lead (for handshake tracking)
            
        Returns:
            EndorsementRequest with drafted email content
        """
        # Validate broker contact
        if not signal.broker_contact:
            raise ValueError(f"Signal {signal.signal_id} missing broker contact")
        
        if not signal.broker_contact.has_valid_contact():
            raise ValueError(f"Signal {signal.signal_id} has invalid broker contact info")
        
        # Determine urgency based on missing endorsements
        urgency = self._calculate_urgency(signal)
        
        # Get required endorsements for each agency
        all_required = []
        for agency in signal.agency_requirements:
            all_required.extend(self.AGENCY_ENDORSEMENTS.get(agency, []))
        
        # Remove duplicates while preserving order
        required_endorsements = list(dict.fromkeys(all_required))
        
        # Draft email content
        subject, body = self._draft_email(signal, required_endorsements, urgency)
        
        # NYC 2027: Legal Sandbox scan for strict liability triggers
        legal_sandbox = get_legal_sandbox()
        recipient_email = (
            signal.broker_contact.broker_email.value 
            if signal.broker_contact.broker_email 
            else "unknown@broker.com"
        )
        
        proof_id = f"PROOF-{signal.signal_id}-{datetime.now().timestamp()}"
        governance_proof = legal_sandbox.scan_content(
            proof_id=proof_id,
            content_type="endorsement_request",
            subject_line=subject,
            body_text=body,
            recipient_email=recipient_email,
            nyc_codes=["RCNY §101-08"]  # NYC insurance codes
        )
        
        # Create agent handshake for governance audit (Task 3)
        handshake = AgentHandshake(
            from_agent=from_agent,
            to_agent=self.AGENT_ID,
            handshake_timestamp=datetime.now(),
            transition_reason=f"Fix compliance gaps for {signal.project_name}",
            data_passed={
                "signal_id": signal.signal_id,
                "project_id": signal.project_id,
                "missing_endorsements": signal.missing_endorsements,
                "insurance_gaps": signal.insurance_gaps,
                "agency_requirements": [a.value for a in signal.agency_requirements],
                "legal_sandbox_status": governance_proof.sandbox_status.value
            },
            validation_status="handoff_validated"
        )
        
        # Update decision proof reasoning to include legal sandbox
        reasoning_chain = [
            f"Detected {len(signal.insurance_gaps)} insurance gaps",
            f"Project requires {len(signal.agency_requirements)} agency endorsements",
            f"Broker contact validated: {signal.broker_contact.has_valid_contact()}",
            f"Urgency level: {urgency}",
            f"Drafted {len(required_endorsements)} endorsement requests",
            f"Legal Sandbox: {governance_proof.sandbox_status.value}",
            f"Triggers detected: {len(governance_proof.triggers_detected)}",
            f"Risk score: {governance_proof.risk_score:.1f}/10"
        ]
        
        # Add warning if sending is blocked
        if governance_proof.send_blocked:
            reasoning_chain.append(f"⚠️ SENDING BLOCKED: {governance_proof.block_reason}")
        
        # Create decision proof for XAI
        decision_proof = DecisionProof(
            agent_id=self.AGENT_ID,
            timestamp=datetime.now(),
            logic_citation="ConComply-Scope Outreach Bridge Policy 2027; NYC Legal Sandbox",
            confidence_score=0.95,
            decision_type="outreach",
            input_data={
                "signal_id": signal.signal_id,
                "project_name": signal.project_name,
                "contractor": signal.contractor_name,
                "agencies": [a.value for a in signal.agency_requirements],
                "gaps": signal.insurance_gaps,
                "governance_proof_id": proof_id
            },
            output_action=f"Draft endorsement request to {signal.broker_contact.broker_name.value}",
            reasoning_chain=reasoning_chain,
            agent_handshake=handshake
        )
        
        # Generate unique request ID
        request_id = hashlib.sha256(
            f"{signal.signal_id}-{datetime.now().isoformat()}".encode()
        ).hexdigest()[:16]
        
        # Track cost
        self._track_cost()
        
        # Create endorsement request
        request = EndorsementRequest(
            request_id=request_id,
            signal_id=signal.signal_id,
            project_name=signal.project_name,
            contractor_name=signal.contractor_name,
            broker_contact=signal.broker_contact,
            agency_requirement=signal.agency_requirements[0] if signal.agency_requirements else AgencyRequirement.SCA,
            required_endorsements=required_endorsements,
            urgency_level=urgency,
            subject_line=subject,
            email_body=body,
            decision_proof=decision_proof
        )
        
        self.requests_drafted += 1
        
        return request
    
    def _calculate_urgency(self, signal: ScopeSignal) -> str:
        """Calculate urgency level based on gaps and project status."""
        gap_count = len(signal.missing_endorsements) + len(signal.insurance_gaps)
        
        if gap_count >= 5:
            return "critical"
        elif gap_count >= 3:
            return "high"
        else:
            return "standard"
    
    def _draft_email(
        self,
        signal: ScopeSignal,
        endorsements: List[str],
        urgency: str
    ) -> tuple[str, str]:
        """
        Draft email subject and body.
        
        Returns:
            Tuple of (subject, body)
        """
        # Get broker name
        broker_name = signal.broker_contact.broker_name.value
        
        # Subject line
        urgency_prefix = "URGENT: " if urgency == "critical" else ""
        subject = f"{urgency_prefix}Endorsement Request - {signal.project_name}"
        
        # Body
        body = f"""Dear {broker_name},

We are preparing to bid on the following project and require specific insurance endorsements to meet agency compliance requirements:

PROJECT DETAILS:
- Project Name: {signal.project_name}
- Project Address: {signal.project_address}
- Contractor: {signal.contractor_name}
- Agencies: {', '.join([a.value for a in signal.agency_requirements])}

REQUIRED ENDORSEMENTS:
{self._format_endorsement_list(endorsements)}

COMPLIANCE GAPS IDENTIFIED:
{self._format_gaps(signal.insurance_gaps)}

URGENCY: {urgency.upper()}
We need these endorsements to proceed with our bid submission. Please provide updated certificates with these endorsements at your earliest convenience.

NEXT STEPS:
1. Review the required endorsements above
2. Confirm availability with your carrier
3. Provide timeline for endorsement issuance
4. Send updated certificate of insurance

If you have any questions or need additional information, please contact us immediately.

Thank you for your prompt attention to this matter.

Best regards,
ConComply Action Center
Automated Compliance Management System

---
Generated by BrokerLiaison Agent v2.0
Cost per request: ${self.TOKEN_COST_PER_1K * self.AVERAGE_TOKENS_PER_DRAFT / 1000:.4f}
"""
        
        return subject, body
    
    def _format_endorsement_list(self, endorsements: List[str]) -> str:
        """Format endorsements as numbered list."""
        return '\n'.join([f"{i+1}. {e}" for i, e in enumerate(endorsements)])
    
    def _format_gaps(self, gaps: List[str]) -> str:
        """Format compliance gaps as bullet list."""
        if not gaps:
            return "- None (preventive request)"
        return '\n'.join([f"- {g}" for g in gaps])
    
    def _track_cost(self):
        """Track cost for efficiency monitoring."""
        cost = (self.AVERAGE_TOKENS_PER_DRAFT / 1000) * self.TOKEN_COST_PER_1K
        self.total_cost += cost
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get agent statistics for monitoring."""
        avg_cost = self.total_cost / self.requests_drafted if self.requests_drafted > 0 else 0
        
        return {
            "agent_id": self.AGENT_ID,
            "requests_drafted": self.requests_drafted,
            "total_cost_usd": self.total_cost,
            "avg_cost_per_request": avg_cost,
            "meets_efficiency_target": avg_cost <= 0.007,  # $0.007/doc target
            "target_cost": 0.007
        }
