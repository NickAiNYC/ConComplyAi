"""
Fixer Agent Outreach Module - Autonomous Remediation Email Drafting
Implements the final link in Scout → Guard → Fixer Triple Handshake

MISSION:
When Guard detects compliance gaps, Fixer autonomously drafts remediation
emails to insurance brokers with 'Senior NYC Subcontractor' tone.

BINDING CONSTRAINTS:
- MUST cite specific NYC code (e.g., RCNY 101-08) or Agency spec (SCA/DDC)
- MUST include NYC DOB Job Number from Scout
- MUST include Correction Link for broker to upload new document
- MUST generate HandshakeV2 pointing back to Guard's DecisionProof
- MUST produce AuditProof object for Veteran Dashboard
- Cost target: Total pipeline (Scout + Guard + Fixer) < $0.005/doc
"""

import hashlib
import json
from typing import Dict, Any, List, Optional, Literal
from datetime import datetime
from pathlib import Path
from pydantic import BaseModel, Field

from packages.core.agent_protocol import (
    AgentRole, AgentHandshakeV2, AgentOutputProtocol
)
from packages.core.audit import (
    DecisionProof, LogicCitation, ComplianceStandard,
    create_decision_proof
)
from packages.core.telemetry import track_agent_cost


# Cost constants for transparent cost model
TEMPLATE_GENERATION_COST_USD = 0.0001  # Minimal cost for template-based email generation
DEFICIENCY_REPORT_INPUT_TOKENS = 200   # Average tokens for reading deficiency report
EMAIL_DRAFT_OUTPUT_TOKENS = 400         # Average tokens for drafting email


class DeficiencyReport(BaseModel):
    """
    Structured deficiency report from Guard Agent
    Contains all information needed to draft remediation email
    """
    document_id: str = Field(description="Document identifier from Guard")
    contractor_name: str = Field(description="Name of the contractor/insured")
    broker_name: Optional[str] = Field(default=None, description="Insurance broker name if available")
    broker_email: Optional[str] = Field(default=None, description="Insurance broker email")
    
    # Deficiency details
    deficiencies: List[str] = Field(description="List of specific compliance gaps")
    citations: List[str] = Field(
        default_factory=list,
        description="NYC codes/regulations that were violated"
    )
    
    # Context
    project_id: str = Field(description="Project identifier from handshake chain")
    permit_number: Optional[str] = Field(default=None, description="DOB permit number if from Scout")
    project_address: Optional[str] = Field(default=None, description="Construction site address")
    
    # Metadata
    validation_date: datetime = Field(default_factory=datetime.utcnow)
    severity: Literal["CRITICAL", "HIGH", "MEDIUM"] = Field(
        default="HIGH",
        description="Severity of deficiencies"
    )


class COIMetadata(BaseModel):
    """
    Certificate of Insurance metadata for context
    """
    document_type: str = Field(default="Certificate of Insurance")
    page_count: int = Field(default=1, description="Number of pages in COI")
    ocr_confidence: float = Field(
        ge=0.0, le=1.0,
        description="OCR quality score"
    )
    upload_date: Optional[datetime] = Field(default=None)


class BrokerMetadata(BaseModel):
    """
    Insurance broker contact information and metadata
    """
    broker_name: str = Field(description="Insurance broker/agency name")
    contact_name: Optional[str] = Field(default=None, description="Broker contact person")
    email: Optional[str] = Field(default=None, description="Broker email address")
    phone: Optional[str] = Field(default=None, description="Broker phone number")
    agency_code: Optional[str] = Field(default=None, description="Insurance agency code")
    
    class Config:
        frozen = True


class EmailDraft(BaseModel):
    """
    Drafted remediation email for broker outreach
    """
    subject: str = Field(description="Email subject line")
    body: str = Field(description="Email body content")
    tone: str = Field(
        default="Construction Professional",
        description="Email tone/style"
    )
    priority: Literal["URGENT", "HIGH", "NORMAL"] = Field(
        default="HIGH",
        description="Email priority level"
    )
    
    # Technical metadata
    cited_regulations: List[str] = Field(
        default_factory=list,
        description="NYC codes cited in email"
    )
    correction_link: str = Field(
        description="URL where broker can upload corrected document"
    )
    
    # Tracking
    draft_id: str = Field(description="Unique draft identifier")
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        frozen = True  # Immutable for audit integrity


class FixerOutput(AgentOutputProtocol):
    """
    Fixer Agent output conforming to AgentOutputProtocol
    Includes drafted email and handshake for audit chain
    """
    email_draft: EmailDraft
    deficiency_report: DeficiencyReport
    
    class Config:
        frozen = True


class OutreachAgent:
    """
    Fixer Agent - Autonomous Remediation Outreach
    
    Inherits from AgentOutputProtocol pattern to maintain consistency
    with Scout and Guard agents in the multi-agent pipeline.
    
    Features:
    - Email drafting with 'Senior NYC Subcontractor' tone (direct, professional)
    - Specific NYC code citations (RCNY 101-08, SCA/DDC specs)
    - Automatic inclusion of NYC DOB Job Number from Scout
    - Correction link generation
    - HandshakeV2 creation for audit chain
    - AuditProof generation for Veteran Dashboard
    - Cost tracking via telemetry decorator
    """
    
    def __init__(self, base_upload_url: str = "https://concomplai.com/upload"):
        """
        Initialize Fixer Agent
        
        Args:
            base_upload_url: Base URL for correction document uploads
        """
        self.base_upload_url = base_upload_url
    
    def generate_remediation_draft(
        self,
        deficiency_report: DeficiencyReport,
        broker_metadata: BrokerMetadata,
        parent_handshake: Optional[AgentHandshakeV2] = None
    ) -> Dict[str, Any]:
        """
        Generate remediation email draft for insurance broker
        
        This is the NEW core Fixer functionality per updated requirements:
        1. Analyzes deficiencies from Guard
        2. Drafts email in 'Senior NYC Subcontractor' tone
        3. Cites specific NYC regulations
        4. Includes NYC DOB Job Number from Scout
        5. Includes correction link
        6. Creates HandshakeV2 for audit chain
        7. Produces AuditProof for Veteran Dashboard
        
        Args:
            deficiency_report: Structured deficiency data from Guard
            broker_metadata: Insurance broker contact information
            parent_handshake: Guard's handshake (for audit chain)
        
        Returns:
            Dict containing:
            - email_draft: EmailDraft object
            - handshake: AgentHandshakeV2 for next agent
            - fixer_output: FixerOutput conforming to AgentOutputProtocol
            - decision_proof_obj: DecisionProof object (AuditProof for Dashboard)
            - cost_usd: Processing cost
            - input_tokens: Token usage
            - output_tokens: Token usage
        """
        # Generate correction link with document ID
        correction_link = f"{self.base_upload_url}?doc_id={deficiency_report.document_id}&project_id={deficiency_report.project_id}"
        
        # Determine priority based on severity
        priority_map = {
            "CRITICAL": "URGENT",
            "HIGH": "HIGH",
            "MEDIUM": "NORMAL"
        }
        priority = priority_map.get(deficiency_report.severity, "HIGH")
        
        # Draft email components with Senior NYC Subcontractor tone
        subject = self._draft_subject_subcontractor_tone(deficiency_report, priority)
        body = self._draft_body_subcontractor_tone(
            deficiency_report=deficiency_report,
            broker_metadata=broker_metadata,
            correction_link=correction_link
        )
        
        # Extract cited regulations
        cited_regulations = self._extract_regulations(deficiency_report)
        
        # Generate unique draft ID
        draft_id = f"FIXER-{deficiency_report.document_id}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        
        # Create email draft
        email_draft = EmailDraft(
            subject=subject,
            body=body,
            tone="Senior NYC Subcontractor",
            priority=priority,
            cited_regulations=cited_regulations,
            correction_link=correction_link,
            draft_id=draft_id
        )
        
        # Create decision proof (AuditProof for Veteran Dashboard)
        logic_citations = self._create_logic_citations(deficiency_report)
        
        reasoning = (
            f"Fixer analyzed {len(deficiency_report.deficiencies)} compliance deficiencies "
            f"from Guard validation of document {deficiency_report.document_id}. "
            f"Drafted remediation email to {broker_metadata.broker_name} "
            f"citing {len(cited_regulations)} specific NYC regulations. "
            f"Email includes NYC DOB Job Number {deficiency_report.permit_number or 'N/A'} and correction link."
        )
        
        decision_proof = create_decision_proof(
            agent_name="Fixer",
            decision="REMEDIATION_DRAFTED",
            input_data={
                "document_id": deficiency_report.document_id,
                "project_id": deficiency_report.project_id,
                "permit_number": deficiency_report.permit_number,
                "deficiency_count": len(deficiency_report.deficiencies),
                "severity": deficiency_report.severity,
                "broker": broker_metadata.broker_name,
            },
            logic_citations=logic_citations,
            reasoning=reasoning,
            confidence=0.90,
            risk_level="MEDIUM",
            estimated_financial_impact=None,
            cost_usd=0.0  # Will be filled by decorator if used
        )
        
        # Create Fixer handshake for audit chain
        handshake = self._create_fixer_handshake(
            deficiency_report=deficiency_report,
            decision_proof_hash=decision_proof.proof_hash,
            parent_handshake=parent_handshake
        )
        
        # Token usage estimation (email drafting uses minimal LLM calls)
        input_tokens = DEFICIENCY_REPORT_INPUT_TOKENS
        output_tokens = EMAIL_DRAFT_OUTPUT_TOKENS
        
        # Calculate cost
        cost_usd = TEMPLATE_GENERATION_COST_USD
        
        # Create FixerOutput conforming to AgentOutputProtocol
        fixer_output = FixerOutput(
            handshake=handshake,
            decision_proof_hash=decision_proof.proof_hash,
            processing_cost_usd=cost_usd,
            confidence_score=0.90,
            agent_name=AgentRole.FIXER,
            email_draft=email_draft,
            deficiency_report=deficiency_report
        )
        
        return {
            "email_draft": email_draft,
            "handshake": handshake,
            "fixer_output": fixer_output,
            "decision_proof_obj": decision_proof,  # AuditProof for Veteran Dashboard
            "audit_proof": decision_proof,  # Alias for clarity
            "cost_usd": cost_usd,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "project_id": deficiency_report.project_id,
        }
    
    
    def _draft_subject_subcontractor_tone(
        self,
        deficiency_report: DeficiencyReport,
        priority: str
    ) -> str:
        """
        Draft subject line with Senior NYC Subcontractor tone
        Direct, professional, includes DOB Job Number
        
        Args:
            deficiency_report: Deficiency details
            priority: Email priority (URGENT/HIGH/NORMAL)
        
        Returns:
            Subject line string
        """
        prefix = ""
        if priority == "URGENT":
            prefix = "URGENT - "
        
        # Include DOB Job Number prominently
        job_ref = ""
        if deficiency_report.permit_number:
            job_ref = f" - DOB Job #{deficiency_report.permit_number}"
        
        return (
            f"{prefix}COI Update Required: {deficiency_report.contractor_name}"
            f"{job_ref}"
        )
    
    def _draft_body_subcontractor_tone(
        self,
        deficiency_report: DeficiencyReport,
        broker_metadata: BrokerMetadata,
        correction_link: str
    ) -> str:
        """
        Draft email body with Senior NYC Subcontractor tone
        
        Tone characteristics:
        - Direct and no-nonsense
        - Professional but not overly formal
        - Construction industry language
        - Non-robotic, human voice
        - Action-oriented
        
        Args:
            deficiency_report: Deficiency details
            broker_metadata: Broker contact info
            correction_link: Upload link for corrections
        
        Returns:
            Email body as formatted string
        """
        # Greeting - direct and professional
        contact_name = broker_metadata.contact_name or broker_metadata.broker_name
        greeting = f"{contact_name},"
        
        # Opening - direct and specific
        job_ref = f"DOB Job #{deficiency_report.permit_number}" if deficiency_report.permit_number else "this project"
        opening = (
            f"\nWe're reviewing the COI for {deficiency_report.contractor_name} on {job_ref} "
            f"and need you to update a few items before we can process it.\n"
        )
        
        # Deficiencies - specific and clear
        deficiencies_header = "\n**Items to Fix:**\n"
        deficiency_items = []
        
        for i, deficiency in enumerate(deficiency_report.deficiencies, 1):
            # Find corresponding citation if available
            citation_note = ""
            if i <= len(deficiency_report.citations):
                citation = deficiency_report.citations[i-1]
                # Make citation more readable
                citation_clean = citation.replace("_", " ").replace("NYC ", "")
                citation_note = f" (per {citation_clean})"
            
            deficiency_items.append(f"{i}. {deficiency}{citation_note}")
        
        deficiencies_text = "\n".join(deficiency_items)
        
        # NYC DOB Job reference for context
        job_context = ""
        if deficiency_report.permit_number and deficiency_report.project_address:
            job_context = f"\n**Project:** DOB Job #{deficiency_report.permit_number} - {deficiency_report.project_address}\n"
        
        # Action items - clear and direct
        action_items = f"""
**What We Need:**

Upload the updated COI here: {correction_link}

Reference this doc ID when you upload: {deficiency_report.document_id}

We'll review it same day once it's in.
"""
        
        # Timeline - direct
        timeline = """
**Timeline:** Need this within 48 hours to keep the project moving.
"""
        
        # Closing - professional but warm
        closing = f"""
Thanks,

Project Team
{deficiency_report.project_id}
"""
        
        # Assemble full email
        body = (
            f"{greeting}\n"
            f"{opening}\n"
            f"{deficiencies_header}\n"
            f"{deficiencies_text}\n"
            f"{job_context}\n"
            f"{action_items}\n"
            f"{timeline}\n"
            f"{closing}"
        )
        
        return body
    
    def draft_broker_email(
        self,
        deficiency_report: DeficiencyReport,
        coi_metadata: COIMetadata,
        parent_handshake: Optional[AgentHandshakeV2] = None
    ) -> Dict[str, Any]:
        """
        Draft remediation email to insurance broker
        
        This is the core Fixer functionality:
        1. Analyzes deficiencies from Guard
        2. Drafts high-EQ professional email
        3. Cites specific NYC regulations
        4. Includes correction link
        5. Creates HandshakeV2 for audit chain
        
        Args:
            deficiency_report: Structured deficiency data from Guard
            coi_metadata: COI document metadata
            parent_handshake: Guard's handshake (for audit chain)
        
        Returns:
            Dict containing:
            - email_draft: EmailDraft object
            - handshake: AgentHandshakeV2 for next agent
            - fixer_output: FixerOutput conforming to AgentOutputProtocol
            - decision_proof_obj: DecisionProof object
            - cost_usd: Processing cost
            - input_tokens: Token usage
            - output_tokens: Token usage
        """
        # Generate correction link with document ID
        correction_link = f"{self.base_upload_url}?doc_id={deficiency_report.document_id}&project_id={deficiency_report.project_id}"
        
        # Determine priority based on severity
        priority_map = {
            "CRITICAL": "URGENT",
            "HIGH": "HIGH",
            "MEDIUM": "NORMAL"
        }
        priority = priority_map.get(deficiency_report.severity, "HIGH")
        
        # Draft email components
        subject = self._draft_subject(deficiency_report, priority)
        body = self._draft_body(
            deficiency_report=deficiency_report,
            coi_metadata=coi_metadata,
            correction_link=correction_link
        )
        
        # Extract cited regulations
        cited_regulations = self._extract_regulations(deficiency_report)
        
        # Generate unique draft ID
        draft_id = f"FIXER-{deficiency_report.document_id}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        
        # Create email draft
        email_draft = EmailDraft(
            subject=subject,
            body=body,
            tone="Construction Professional",
            priority=priority,
            cited_regulations=cited_regulations,
            correction_link=correction_link,
            draft_id=draft_id
        )
        
        # Create decision proof for Fixer's work
        logic_citations = self._create_logic_citations(deficiency_report)
        
        reasoning = (
            f"Fixer analyzed {len(deficiency_report.deficiencies)} compliance deficiencies "
            f"from Guard validation of document {deficiency_report.document_id}. "
            f"Drafted remediation email to {deficiency_report.broker_name or 'insurance broker'} "
            f"citing {len(cited_regulations)} specific NYC regulations. "
            f"Email includes correction link for document resubmission."
        )
        
        decision_proof = create_decision_proof(
            agent_name="Fixer",
            decision="REMEDIATION_DRAFTED",
            input_data={
                "document_id": deficiency_report.document_id,
                "project_id": deficiency_report.project_id,
                "deficiency_count": len(deficiency_report.deficiencies),
                "severity": deficiency_report.severity,
            },
            logic_citations=logic_citations,
            reasoning=reasoning,
            confidence=0.90,
            risk_level="MEDIUM",
            estimated_financial_impact=None,
            cost_usd=0.0  # Will be filled by decorator if used
        )
        
        # Create Fixer handshake for audit chain
        handshake = self._create_fixer_handshake(
            deficiency_report=deficiency_report,
            decision_proof_hash=decision_proof.proof_hash,
            parent_handshake=parent_handshake
        )
        
        # Token usage estimation (email drafting uses minimal LLM calls)
        # For rule-based drafting, we use minimal tokens
        input_tokens = DEFICIENCY_REPORT_INPUT_TOKENS
        output_tokens = EMAIL_DRAFT_OUTPUT_TOKENS
        
        # Calculate cost (will be overridden by decorator if used)
        cost_usd = TEMPLATE_GENERATION_COST_USD
        
        # Create FixerOutput conforming to AgentOutputProtocol
        fixer_output = FixerOutput(
            handshake=handshake,
            decision_proof_hash=decision_proof.proof_hash,
            processing_cost_usd=cost_usd,
            confidence_score=0.90,
            agent_name=AgentRole.FIXER,
            email_draft=email_draft,
            deficiency_report=deficiency_report
        )
        
        return {
            "email_draft": email_draft,
            "handshake": handshake,
            "fixer_output": fixer_output,
            "decision_proof_obj": decision_proof,
            "cost_usd": cost_usd,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "project_id": deficiency_report.project_id,
        }
    
    def _draft_subject(
        self,
        deficiency_report: DeficiencyReport,
        priority: str
    ) -> str:
        """
        Draft professional email subject line
        
        Args:
            deficiency_report: Deficiency details
            priority: Email priority (URGENT/HIGH/NORMAL)
        
        Returns:
            Subject line string
        """
        prefix = ""
        if priority == "URGENT":
            prefix = "🚨 URGENT: "
        
        # Include permit number if available (from Scout)
        permit_ref = ""
        if deficiency_report.permit_number:
            permit_ref = f" - Permit #{deficiency_report.permit_number}"
        
        return (
            f"{prefix}COI Revision Required: {deficiency_report.contractor_name}"
            f"{permit_ref}"
        )
    
    def _draft_body(
        self,
        deficiency_report: DeficiencyReport,
        coi_metadata: COIMetadata,
        correction_link: str
    ) -> str:
        """
        Draft high-EQ professional email body
        
        Uses 'Construction Professional' tone:
        - Direct and clear
        - Respectful and collaborative
        - Specific regulatory citations
        - Action-oriented
        - NOT 'AI-speak' or overly formal
        
        Args:
            deficiency_report: Deficiency details
            coi_metadata: COI metadata
            correction_link: Upload link for corrections
        
        Returns:
            Email body as formatted string
        """
        # Greeting
        broker_name = deficiency_report.broker_name or "Insurance Broker"
        greeting = f"Hi {broker_name},"
        
        # Opening - set context
        opening = (
            f"\nWe reviewed the Certificate of Insurance for **{deficiency_report.contractor_name}** "
            f"(Project: {deficiency_report.project_id}) and found a few items that need attention "
            f"before we can approve it for the project.\n"
        )
        
        # Deficiencies section - specific and clear
        deficiencies_header = "\n**What Needs to Be Fixed:**\n"
        deficiency_items = []
        
        for i, deficiency in enumerate(deficiency_report.deficiencies, 1):
            # Find corresponding citation if available
            citation_note = ""
            if i <= len(deficiency_report.citations):
                citation = deficiency_report.citations[i-1]
                citation_note = f" *(Required by {citation})*"
            
            deficiency_items.append(f"{i}. {deficiency}{citation_note}")
        
        deficiencies_text = "\n".join(deficiency_items)
        
        # Regulatory context - cite specific codes
        regulatory_section = self._draft_regulatory_context(deficiency_report)
        
        # Action items - clear next steps
        action_items = f"""
**Next Steps:**

1. **Update the COI** to address all items listed above
2. **Re-submit via this link:** {correction_link}
3. **Reference Document ID:** {deficiency_report.document_id}

Our system will automatically re-validate within minutes of your upload.
"""
        
        # Timeline and support
        timeline_support = """
**Timeline:**
Please submit the updated COI within 48 hours to keep the project on track.

**Questions?**
Feel free to reach out if any of these requirements need clarification. We're here to help get this sorted quickly.
"""
        
        # Closing - professional and warm
        closing = f"""
Thanks for your attention to this.

Best regards,
ConComplyAi Compliance Team
Project: {deficiency_report.project_id}
"""
        
        # Assemble full email
        body = (
            f"{greeting}\n"
            f"{opening}\n"
            f"{deficiencies_header}\n"
            f"{deficiencies_text}\n"
            f"{regulatory_section}\n"
            f"{action_items}\n"
            f"{timeline_support}\n"
            f"{closing}"
        )
        
        return body
    
    def _draft_regulatory_context(
        self,
        deficiency_report: DeficiencyReport
    ) -> str:
        """
        Draft regulatory context section with specific NYC codes
        
        Args:
            deficiency_report: Deficiency details with citations
        
        Returns:
            Formatted regulatory context text
        """
        if not deficiency_report.citations:
            return ""
        
        context = "\n**Regulatory Background:**\n"
        
        # Map citations to friendly explanations
        citation_explanations = {
            "NYC_RCNY_101_08": "NYC RCNY 101-08 requires that the certificate holder be named as an Additional Insured on the General Liability policy.",
            "ISO_GL_MINIMUM": "NYC construction projects require minimum General Liability coverage of $2M per occurrence / $4M aggregate.",
            "WAIVER_SUBROGATION": "Waiver of Subrogation is required to protect the certificate holder from claims.",
            "PER_PROJECT_AGGREGATE": "A separate Per Project Aggregate is required to ensure adequate coverage for this specific project.",
            "SCA": "NYC School Construction Authority (SCA) projects have enhanced insurance requirements per SCA specifications.",
            "DDC": "NYC Department of Design and Construction (DDC) requires specific insurance endorsements per DDC contracts.",
        }
        
        # Build context from citations
        explanations = []
        for citation in deficiency_report.citations:
            # Extract standard name from citation if it's a full string
            for key, explanation in citation_explanations.items():
                if key in citation or key.replace("_", " ") in citation:
                    explanations.append(f"- {explanation}")
                    break
        
        # If we found explanations, add them
        if explanations:
            context += "\n".join(explanations)
            context += "\n"
        
        return context
    
    def _extract_regulations(
        self,
        deficiency_report: DeficiencyReport
    ) -> List[str]:
        """
        Extract NYC regulations/codes from deficiency report
        
        Args:
            deficiency_report: Deficiency details
        
        Returns:
            List of regulation codes
        """
        regulations = []
        
        # From citations
        for citation in deficiency_report.citations:
            if "RCNY" in citation:
                regulations.append("NYC RCNY 101-08")
            if "SCA" in citation:
                regulations.append("SCA Construction Standards")
            if "DDC" in citation:
                regulations.append("DDC Insurance Requirements")
            if "ISO_GL" in citation:
                regulations.append("ISO General Liability Standards")
            if "WAIVER" in citation:
                regulations.append("Waiver of Subrogation Requirements")
        
        # From deficiency text
        for deficiency in deficiency_report.deficiencies:
            deficiency_upper = deficiency.upper()
            if "ADDITIONAL INSURED" in deficiency_upper and "NYC RCNY 101-08" not in regulations:
                regulations.append("NYC RCNY 101-08")
            if "$2M" in deficiency or "$2,000,000" in deficiency:
                if "ISO General Liability Standards" not in regulations:
                    regulations.append("ISO General Liability Standards")
        
        return list(set(regulations))  # Remove duplicates
    
    def _create_logic_citations(
        self,
        deficiency_report: DeficiencyReport
    ) -> List[LogicCitation]:
        """
        Create logic citations for DecisionProof
        
        Args:
            deficiency_report: Deficiency details
        
        Returns:
            List of LogicCitation objects
        """
        citations = []
        
        # Map deficiencies to compliance standards
        for deficiency in deficiency_report.deficiencies:
            deficiency_lower = deficiency.lower()
            
            if "additional insured" in deficiency_lower:
                citations.append(LogicCitation(
                    standard=ComplianceStandard.NYC_RCNY_101_08,
                    clause="§101-08",
                    interpretation="Additional Insured endorsement required for NYC construction projects",
                    confidence=0.95
                ))
            
            if "waiver" in deficiency_lower and "subrogation" in deficiency_lower:
                citations.append(LogicCitation(
                    standard=ComplianceStandard.WAIVER_SUBROGATION,
                    clause="Standard Waiver",
                    interpretation="Waiver of Subrogation protects certificate holder from claims",
                    confidence=0.95
                ))
            
            if "$2m" in deficiency_lower or "$2,000,000" in deficiency_lower or "coverage" in deficiency_lower:
                citations.append(LogicCitation(
                    standard=ComplianceStandard.ISO_GL_MINIMUM,
                    clause="Minimum Coverage",
                    interpretation="General Liability minimum $2M per occurrence / $4M aggregate",
                    confidence=0.90
                ))
            
            if "aggregate" in deficiency_lower and "project" in deficiency_lower:
                citations.append(LogicCitation(
                    standard=ComplianceStandard.PER_PROJECT_AGGREGATE,
                    clause="Per Project",
                    interpretation="Separate aggregate required for this specific project",
                    confidence=0.90
                ))
        
        # If no specific citations, add a general one
        if not citations:
            citations.append(LogicCitation(
                standard=ComplianceStandard.NYC_BC_3301,
                clause="General Compliance",
                interpretation="COI must meet NYC construction compliance standards",
                confidence=0.80
            ))
        
        return citations
    
    def _create_fixer_handshake(
        self,
        deficiency_report: DeficiencyReport,
        decision_proof_hash: str,
        parent_handshake: Optional[AgentHandshakeV2] = None
    ) -> AgentHandshakeV2:
        """
        Create Fixer agent handshake for audit chain
        
        Links back to Guard's DecisionProof via parent_handshake
        
        Args:
            deficiency_report: Deficiency details
            decision_proof_hash: SHA-256 hash from Fixer's DecisionProof
            parent_handshake: Guard's handshake (for chain linkage)
        
        Returns:
            AgentHandshakeV2 object
        """
        return AgentHandshakeV2(
            source_agent=AgentRole.FIXER,
            target_agent=None,  # Fixer is typically terminal (email sent)
            project_id=deficiency_report.project_id,
            decision_hash=decision_proof_hash,
            parent_handshake_id=parent_handshake.decision_hash if parent_handshake else None,
            transition_reason="remediation_email_drafted",
            metadata={
                "document_id": deficiency_report.document_id,
                "deficiency_count": len(deficiency_report.deficiencies),
                "severity": deficiency_report.severity,
                "broker_name": deficiency_report.broker_name,
                "contractor_name": deficiency_report.contractor_name,
            }
        )


# Convenience function for decorated usage with telemetry
@track_agent_cost(agent_name="Fixer", model_name="claude-3-haiku")
def draft_broker_email(
    deficiency_report: DeficiencyReport,
    coi_metadata: COIMetadata,
    parent_handshake: Optional[AgentHandshakeV2] = None,
    base_upload_url: str = "https://concomplai.com/upload"
) -> Dict[str, Any]:
    """
    Draft broker email with automatic cost tracking
    
    This is the main entry point for the Fixer agent with telemetry.
    
    Args:
        deficiency_report: Structured deficiency data from Guard
        coi_metadata: COI document metadata
        parent_handshake: Guard's handshake (for audit chain)
        base_upload_url: Base URL for document uploads
    
    Returns:
        Dict with email_draft, handshake, fixer_output, decision_proof_obj, cost_usd, tokens
    """
    agent = OutreachAgent(base_upload_url=base_upload_url)
    return agent.draft_broker_email(
        deficiency_report=deficiency_report,
        coi_metadata=coi_metadata,
        parent_handshake=parent_handshake
    )
