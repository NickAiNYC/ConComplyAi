"""
Workflow Manager - Scout → Guard → Fixer Triple Handshake
Orchestrates the complete multi-agent compliance pipeline

MISSION:
Detect Guard's NON_COMPLIANT status and automatically trigger Fixer for remediation.
Maintain audit chain integrity across all three agents.

WORKFLOW:
1. Scout discovers opportunity → creates handshake
2. Guard validates COI → creates handshake (may indicate PENDING_FIX)
3. WorkflowManager detects PENDING_FIX → triggers Fixer
4. Fixer drafts remediation email → creates handshake
5. Complete audit chain is verified and logged
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path

from packages.agents.scout.finder import (
    find_opportunities,
    create_scout_handshake,
    Opportunity
)
from packages.agents.guard.core import validate_coi
from packages.agents.fixer.outreach import (
    OutreachAgent,
    DeficiencyReport,
    COIMetadata,
    draft_broker_email
)
from packages.core.agent_protocol import (
    AgentRole,
    AgentHandshakeV2,
    AuditChain
)


class WorkflowManager:
    """
    Manages the Scout → Guard → Fixer triple handshake workflow
    
    Features:
    - Automatic Fixer trigger on Guard non-compliance
    - Audit chain construction and verification
    - Cost tracking across all agents
    - Error handling and retry logic
    """
    
    def __init__(self, base_upload_url: str = "https://concomplai.com/upload"):
        """
        Initialize Workflow Manager
        
        Args:
            base_upload_url: Base URL for correction uploads in Fixer emails
        """
        self.base_upload_url = base_upload_url
        self.outreach_agent = OutreachAgent(base_upload_url=base_upload_url)
    
    def process_opportunity(
        self,
        opportunity: Opportunity,
        scout_handshake: AgentHandshakeV2,
        coi_pdf_path: Path
    ) -> Dict[str, Any]:
        """
        Process a single opportunity through Guard → Fixer pipeline
        
        Args:
            opportunity: Opportunity from Scout
            scout_handshake: Scout's handshake
            coi_pdf_path: Path to COI PDF for validation
        
        Returns:
            Dict containing:
            - guard_result: Guard validation result
            - fixer_result: Fixer result (if triggered)
            - audit_chain: Complete audit chain
            - pipeline_outcome: Final outcome status
        """
        # STEP 1: Guard validates COI
        guard_result = validate_coi(
            pdf_path=coi_pdf_path,
            parent_handshake=scout_handshake,
            project_id=opportunity.to_project_id()
        )
        
        compliance_result = guard_result["compliance_result"]
        guard_handshake = guard_result["handshake"]
        
        # STEP 2: Check if Fixer should be triggered
        should_trigger_fixer = self._should_trigger_fixer(compliance_result.status)
        
        fixer_result = None
        chain_links = [scout_handshake, guard_handshake]
        pipeline_outcome = "BID_READY"
        
        if should_trigger_fixer:
            # STEP 3: Trigger Fixer for remediation
            fixer_result = self._trigger_fixer(
                opportunity=opportunity,
                guard_result=guard_result,
                guard_handshake=guard_handshake
            )
            
            # Add Fixer handshake to chain
            if fixer_result:
                chain_links.append(fixer_result["handshake"])
                pipeline_outcome = "PENDING_FIX"
        else:
            # Determine outcome based on Guard status
            if compliance_result.status == "APPROVED":
                pipeline_outcome = "BID_READY"
            elif compliance_result.status == "REJECTED":
                pipeline_outcome = "REJECTED"
            elif compliance_result.status == "ILLEGIBLE":
                pipeline_outcome = "REJECTED"
        
        # STEP 4: Build audit chain
        total_cost = guard_result["cost_usd"]
        if fixer_result:
            total_cost += fixer_result["cost_usd"]
        
        audit_chain = AuditChain(
            project_id=opportunity.to_project_id(),
            chain_links=chain_links,
            total_cost_usd=total_cost,
            processing_time_seconds=0.5,  # Mock timing
            outcome=pipeline_outcome
        )
        
        # Verify chain integrity
        chain_valid = audit_chain.verify_chain_integrity()
        
        return {
            "guard_result": guard_result,
            "fixer_result": fixer_result,
            "audit_chain": audit_chain,
            "chain_valid": chain_valid,
            "pipeline_outcome": pipeline_outcome,
            "total_cost_usd": total_cost,
        }
    
    def run_full_pipeline(
        self,
        scout_result: Optional[Dict[str, Any]] = None,
        opportunity_index: int = 0,
        coi_pdf_path: Optional[Path] = None
    ) -> Dict[str, Any]:
        """
        Run the complete Scout → Guard → Fixer pipeline
        
        Args:
            scout_result: Pre-computed Scout result (or None to run Scout)
            opportunity_index: Which opportunity to process (default: 0)
            coi_pdf_path: Path to COI PDF (if None, uses mock path)
        
        Returns:
            Dict containing complete pipeline results and audit chain
        """
        # STEP 1: Scout discovers opportunities (if not provided)
        if scout_result is None:
            scout_result = find_opportunities(
                hours_lookback=24,
                min_estimated_fee=5000.0,
                job_types=["NB", "A1"],
                use_mock=True
            )
        
        opportunities = scout_result["opportunities"]
        
        if not opportunities:
            return {
                "success": False,
                "error": "No opportunities found by Scout",
                "scout_result": scout_result,
            }
        
        # Select opportunity
        if opportunity_index >= len(opportunities):
            opportunity_index = 0
        
        opportunity = opportunities[opportunity_index]
        scout_proof = scout_result["decision_proof"]
        
        # Create Scout handshake
        scout_handshake = create_scout_handshake(
            opportunity=opportunity,
            decision_proof_hash=scout_proof.proof_hash,
            target_agent=AgentRole.GUARD
        )
        
        # Use mock COI path if not provided
        if coi_pdf_path is None:
            coi_pdf_path = Path(f"/tmp/mock_coi_{opportunity.to_project_id()}.pdf")
        
        # STEP 2-4: Process through Guard → Fixer pipeline
        pipeline_result = self.process_opportunity(
            opportunity=opportunity,
            scout_handshake=scout_handshake,
            coi_pdf_path=coi_pdf_path
        )
        
        # Combine results
        return {
            "success": True,
            "scout_result": scout_result,
            "opportunity": opportunity,
            "scout_handshake": scout_handshake,
            **pipeline_result,
        }
    
    def _should_trigger_fixer(self, guard_status: str) -> bool:
        """
        Determine if Fixer should be triggered based on Guard status
        
        Args:
            guard_status: Status from Guard validation
        
        Returns:
            True if Fixer should be triggered
        """
        # Trigger Fixer for these statuses:
        # - PENDING_FIX: Deficiencies found but fixable
        # - REJECTED: Significant deficiencies (though may be terminal)
        
        trigger_statuses = ["PENDING_FIX", "REJECTED"]
        return guard_status in trigger_statuses
    
    def _trigger_fixer(
        self,
        opportunity: Opportunity,
        guard_result: Dict[str, Any],
        guard_handshake: AgentHandshakeV2
    ) -> Optional[Dict[str, Any]]:
        """
        Trigger Fixer agent to draft remediation email
        
        Args:
            opportunity: Opportunity from Scout
            guard_result: Guard validation result
            guard_handshake: Guard's handshake
        
        Returns:
            Fixer result dict or None if Fixer fails
        """
        compliance_result = guard_result["compliance_result"]
        
        # Build deficiency report from Guard result
        deficiency_report = DeficiencyReport(
            document_id=compliance_result.document_id,
            contractor_name=opportunity.owner_name,
            broker_name=None,  # Could be extracted from COI in production
            broker_email=None,  # Could be extracted from COI in production
            deficiencies=compliance_result.deficiency_list,
            citations=compliance_result.citations,
            project_id=opportunity.to_project_id(),
            permit_number=opportunity.permit_number,
            project_address=opportunity.address,
            validation_date=datetime.utcnow(),
            severity="HIGH" if compliance_result.status == "PENDING_FIX" else "CRITICAL"
        )
        
        # Build COI metadata
        coi_metadata = COIMetadata(
            document_type="Certificate of Insurance",
            page_count=compliance_result.page_count,
            ocr_confidence=compliance_result.ocr_confidence,
            upload_date=None
        )
        
        # Draft remediation email using Fixer
        try:
            fixer_result = draft_broker_email(
                deficiency_report=deficiency_report,
                coi_metadata=coi_metadata,
                parent_handshake=guard_handshake,
                base_upload_url=self.base_upload_url
            )
            return fixer_result
        except Exception as e:
            print(f"ERROR: Fixer failed to draft email: {e}")
            return None
    
    def get_pipeline_summary(self, pipeline_result: Dict[str, Any]) -> str:
        """
        Generate human-readable summary of pipeline execution
        
        Args:
            pipeline_result: Result from run_full_pipeline()
        
        Returns:
            Formatted summary string
        """
        if not pipeline_result.get("success"):
            return f"Pipeline failed: {pipeline_result.get('error', 'Unknown error')}"
        
        opportunity = pipeline_result["opportunity"]
        guard_result = pipeline_result["guard_result"]
        fixer_result = pipeline_result.get("fixer_result")
        audit_chain = pipeline_result["audit_chain"]
        
        lines = [
            "=" * 80,
            "SCOUT → GUARD → FIXER PIPELINE SUMMARY",
            "=" * 80,
            "",
            f"Project: {opportunity.to_project_id()}",
            f"Contractor: {opportunity.owner_name}",
            f"Permit: {opportunity.permit_number}",
            f"Location: {opportunity.address}, {opportunity.borough}",
            "",
            "PIPELINE FLOW:",
            f"  Scout → Guard → {'Fixer' if fixer_result else 'Terminal'}",
            "",
            "COMPLIANCE STATUS:",
            f"  Guard Validation: {guard_result['compliance_result'].status}",
            f"  Confidence: {guard_result['compliance_result'].confidence_score:.2%}",
        ]
        
        if guard_result['compliance_result'].deficiency_list:
            lines.append(f"  Deficiencies: {len(guard_result['compliance_result'].deficiency_list)}")
            for deficiency in guard_result['compliance_result'].deficiency_list[:3]:
                lines.append(f"    - {deficiency}")
            if len(guard_result['compliance_result'].deficiency_list) > 3:
                lines.append(f"    ... and {len(guard_result['compliance_result'].deficiency_list) - 3} more")
        
        if fixer_result:
            lines.extend([
                "",
                "FIXER REMEDIATION:",
                f"  Email drafted for: {fixer_result['email_draft'].subject}",
                f"  Priority: {fixer_result['email_draft'].priority}",
                f"  Cited regulations: {', '.join(fixer_result['email_draft'].cited_regulations)}",
                f"  Correction link: {fixer_result['email_draft'].correction_link}",
            ])
        
        lines.extend([
            "",
            "AUDIT CHAIN:",
            f"  Links: {len(audit_chain.chain_links)}",
            f"  Valid: {'✅ YES' if pipeline_result['chain_valid'] else '❌ NO'}",
            f"  Outcome: {audit_chain.outcome}",
            "",
            "COST ANALYSIS:",
            f"  Total: ${pipeline_result['total_cost_usd']:.6f}",
            f"  Target: $0.005000",
            f"  Status: {'✅ UNDER TARGET' if pipeline_result['total_cost_usd'] < 0.005 else '⚠️  OVER TARGET'}",
            "=" * 80,
        ])
        
        return "\n".join(lines)


# Factory function
def create_workflow_manager(base_upload_url: str = "https://concomplai.com/upload") -> WorkflowManager:
    """
    Create and return configured WorkflowManager
    
    Args:
        base_upload_url: Base URL for correction uploads
    
    Returns:
        WorkflowManager instance
    """
    return WorkflowManager(base_upload_url=base_upload_url)
