"""
Outreach Agent - Autonomous Correction Request System
Part of the Self-Healing Multi-Agent Suite

Triggers when documents fail validation to automatically:
1. Analyze validation failures
2. Draft specific correction requests
3. Send via mock SendGrid/Twilio
4. Log to immutable audit trail

Cost: $0.0001 per outreach (included in $0.0066/doc efficiency)
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from packages.shared.models import (
    DocumentExtractionState,
    AuditLogEntry,
    DecisionLog,
    AuditAction
)


class OutreachRequest(BaseModel):
    """Outreach communication request"""
    request_id: str
    contractor_id: str
    contractor_name: str
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    
    # Message details
    subject: str
    message: str
    priority: int = Field(ge=1, le=5, description="1=urgent, 5=info")
    
    # Context
    document_id: str
    document_type: str
    validation_errors: List[str]
    
    # Delivery
    delivery_method: str = Field(default="email", description="email, sms, portal")
    sent_at: Optional[datetime] = None
    delivered: bool = Field(default=False)


class OutreachAgent:
    """
    Autonomous agent that handles contractor outreach for corrections
    
    Features:
    - Intelligent error message generation
    - Priority-based routing
    - Mock SendGrid/Twilio integration
    - Audit trail logging
    """
    
    def __init__(self, audit_logger: Optional[Any] = None):
        self.audit_logger = audit_logger
        self.outreach_history: List[OutreachRequest] = []
        
    def analyze_validation_failure(
        self, 
        state: DocumentExtractionState
    ) -> Dict[str, Any]:
        """
        Analyze validation failures and determine correction needs
        
        Returns analysis with specific issues and recommendations
        """
        errors = state.validation_errors
        doc_type = state.document_type.value
        
        # Categorize errors
        missing_fields = []
        expired_items = []
        insufficient_coverage = []
        formatting_issues = []
        
        for error in errors:
            error_lower = error.lower()
            if 'missing' in error_lower or 'not found' in error_lower:
                missing_fields.append(error)
            elif 'expir' in error_lower:
                expired_items.append(error)
            elif 'coverage' in error_lower or 'limit' in error_lower:
                insufficient_coverage.append(error)
            else:
                formatting_issues.append(error)
        
        # Determine priority
        priority = 1  # Default critical
        if expired_items or insufficient_coverage:
            priority = 1  # Critical
        elif missing_fields:
            priority = 2  # High
        else:
            priority = 3  # Medium
        
        return {
            'missing_fields': missing_fields,
            'expired_items': expired_items,
            'insufficient_coverage': insufficient_coverage,
            'formatting_issues': formatting_issues,
            'priority': priority,
            'error_count': len(errors)
        }
    
    def draft_correction_message(
        self,
        document_type: str,
        contractor_name: str,
        analysis: Dict[str, Any]
    ) -> Dict[str, str]:
        """
        Draft specific correction request based on validation failure
        
        Returns subject and message body
        """
        doc_type_friendly = document_type.replace('_', ' ').title()
        errors = []
        
        # Build specific error list
        if analysis['missing_fields']:
            errors.append("**Missing Required Fields:**")
            for error in analysis['missing_fields']:
                errors.append(f"  • {error}")
        
        if analysis['expired_items']:
            errors.append("\n**Expired Items:**")
            for error in analysis['expired_items']:
                errors.append(f"  • {error}")
        
        if analysis['insufficient_coverage']:
            errors.append("\n**Insurance Coverage Issues:**")
            for error in analysis['insufficient_coverage']:
                errors.append(f"  • {error}")
        
        if analysis['formatting_issues']:
            errors.append("\n**Document Quality Issues:**")
            for error in analysis['formatting_issues']:
                errors.append(f"  • {error}")
        
        # Draft subject
        subject = f"Action Required: {doc_type_friendly} Validation Failed"
        if analysis['priority'] == 1:
            subject = f"🚨 URGENT: {subject}"
        
        # Draft message
        message = f"""Dear {contractor_name},

Your recently submitted {doc_type_friendly} has been reviewed by our automated compliance system and requires corrections before approval.

**Document ID:** {{document_id}}
**Validation Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}

**Issues Identified:**

{chr(10).join(errors)}

**Required Action:**
Please resubmit a corrected {doc_type_friendly} addressing all issues listed above within 48 hours to maintain compliance status.

**How to Resubmit:**
1. Log into the ConComplyAi portal
2. Navigate to "Document Upload"
3. Upload the corrected document
4. Reference Document ID: {{document_id}}

Our AI system will re-validate your submission immediately upon upload.

**Questions?**
Contact: compliance@concomplai.com
Phone: (555) 123-4567

This message was automatically generated by ConComplyAi's Self-Healing Compliance System.

Best regards,
ConComplyAi Compliance Team
"""
        
        return {
            'subject': subject,
            'message': message
        }
    
    def send_outreach(
        self,
        contractor_id: str,
        contractor_name: str,
        contact_email: str,
        document_id: str,
        document_type: str,
        validation_errors: List[str],
        delivery_method: str = "email"
    ) -> OutreachRequest:
        """
        Send correction request to contractor
        
        Uses mock SendGrid/Twilio integration
        Returns outreach request with delivery status
        """
        # Analyze failures
        from core.models import DocumentExtractionState, DocumentType
        state = DocumentExtractionState(
            document_id=document_id,
            document_type=DocumentType(document_type),
            validation_errors=validation_errors
        )
        
        analysis = self.analyze_validation_failure(state)
        
        # Draft message
        draft = self.draft_correction_message(
            document_type,
            contractor_name,
            analysis
        )
        
        # Create outreach request
        request = OutreachRequest(
            request_id=f"OUT-{datetime.now().timestamp()}",
            contractor_id=contractor_id,
            contractor_name=contractor_name,
            contact_email=contact_email,
            subject=draft['subject'],
            message=draft['message'].replace('{document_id}', document_id),
            priority=analysis['priority'],
            document_id=document_id,
            document_type=document_type,
            validation_errors=validation_errors,
            delivery_method=delivery_method
        )
        
        # Mock send (in production, use real SendGrid/Twilio)
        success = self._mock_send(request)
        
        if success:
            request.sent_at = datetime.now()
            request.delivered = True
        
        # Store in history
        self.outreach_history.append(request)
        
        # Log to audit trail
        if self.audit_logger:
            self._log_outreach(request, analysis)
        
        return request
    
    def _mock_send(self, request: OutreachRequest) -> bool:
        """
        Mock email/SMS sending
        
        In production, replace with:
        - SendGrid API for email
        - Twilio API for SMS
        - Portal notification system
        """
        print(f"[MOCK_OUTREACH] Sending to {request.contractor_name}")
        print(f"  Method: {request.delivery_method}")
        print(f"  Priority: P{request.priority}")
        print(f"  Subject: {request.subject}")
        print(f"  Email: {request.contact_email}")
        print(f"  Message preview: {request.message[:200]}...")
        
        # Simulate success
        return True
    
    def _log_outreach(self, request: OutreachRequest, analysis: Dict[str, Any]):
        """Log outreach to audit trail"""
        decision = DecisionLog(
            decision_id=request.request_id,
            action=AuditAction.OUTREACH_SENT,
            agent_name="outreach_agent",
            document_id=request.document_id,
            contractor_id=request.contractor_id,
            decision_data={
                'subject': request.subject,
                'priority': request.priority,
                'delivery_method': request.delivery_method,
                'error_count': len(request.validation_errors),
                'analysis': analysis
            },
            reasoning=f"Validation failed with {len(request.validation_errors)} errors. "
                     f"Automatically drafted correction request and sent to contractor.",
            confidence=0.95,  # High confidence in automated messaging
            action_taken=f"Sent {request.delivery_method} to {request.contractor_name}",
            cost_usd=0.0001,  # Negligible cost
            requires_human_review=request.priority == 1  # Critical items need review
        )
        
        if self.audit_logger:
            self.audit_logger.log_decision(decision)
    
    def get_outreach_statistics(self) -> Dict[str, Any]:
        """Get statistics on outreach activities"""
        total = len(self.outreach_history)
        delivered = len([r for r in self.outreach_history if r.delivered])
        by_priority = {}
        
        for request in self.outreach_history:
            by_priority[f"P{request.priority}"] = by_priority.get(f"P{request.priority}", 0) + 1
        
        return {
            'total_sent': total,
            'delivered': delivered,
            'delivery_rate': delivered / total if total > 0 else 0,
            'by_priority': by_priority,
            'by_method': {
                'email': len([r for r in self.outreach_history if r.delivery_method == 'email']),
                'sms': len([r for r in self.outreach_history if r.delivery_method == 'sms'])
            }
        }


# Factory function for easy initialization
def create_outreach_agent(audit_logger=None) -> OutreachAgent:
    """Create and return configured OutreachAgent"""
    return OutreachAgent(audit_logger=audit_logger)
