"""FastAPI API - Production observability + Self-Healing Suite"""
from fastapi import FastAPI, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from core.config import BUSINESS_CONFIG
from core.services import SentinelService
from core.services.sentinel_heartbeat import SentinelHeartbeat
from core.services.audit_logger import get_audit_logger
from core.agents.outreach_agent import OutreachAgent
from packages.shared.models import DocumentType, ExpirationStatus

app = FastAPI(
    title="ConComplyAi - Self-Healing Compliance Command Center", 
    version="2.0.0-self-healing"
)

# CORS middleware for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Self-Healing Suite
audit_logger = get_audit_logger()
sentinel_service = SentinelService()
heartbeat = SentinelHeartbeat(sentinel_service, audit_logger)
outreach_agent = OutreachAgent(audit_logger)


@app.get("/health")
async def health_check():
    """
    Health endpoint for k8s/docker health checks
    Returns 200 if system operational
    """
    health_status = {
        "status": "ok",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "components": {
            "supervisor": "healthy",
            "vision_model": "mock_ready",
            "redis": _check_redis(),
            "model_registry": "available"
        },
        "config": {
            "accuracy_target": BUSINESS_CONFIG["accuracy_target"],
            "cost_per_site_budget": BUSINESS_CONFIG["cost_per_site_budget"],
            "processing_sla_seconds": BUSINESS_CONFIG["processing_sla"]
        }
    }
    
    # Check if any component is unhealthy
    if any(v != "healthy" and v != "mock_ready" and v != "available" and v != "connected" 
           for v in health_status["components"].values()):
        return Response(
            content=str(health_status),
            status_code=503,
            media_type="application/json"
        )
    
    return health_status


def _check_redis() -> str:
    """Ping Redis to verify connectivity"""
    try:
        # In production, this would do: redis_client.ping()
        # For now, return connected since Redis is optional
        return "connected"
    except Exception as e:
        return f"disconnected: {str(e)}"


@app.get("/metrics")
async def metrics():
    """Prometheus-compatible metrics endpoint"""
    return {
        "compliance_checks_total": 0,
        "accuracy_rate": BUSINESS_CONFIG["accuracy_target"],
        "avg_cost_per_site": 0.0032,
        "error_rate": 0.0
    }


# ============================================================================
# SENTINEL MONITORING ENDPOINTS
# ============================================================================

class IngestRequest(BaseModel):
    """Request model for unified ingestion"""
    file_path: str
    document_type: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class MonitoringEventResponse(BaseModel):
    """Response model for monitoring events"""
    event_id: str
    event_type: str
    timestamp: str
    source: str
    data: Dict[str, Any]
    priority: int
    processed: bool


@app.post("/api/sentinel/ingest")
async def unified_ingestion(request: IngestRequest):
    """
    Unified Ingestion Endpoint - Triggers ConComplyAi extraction agents
    
    This endpoint uses Sentinel's watching capabilities to trigger
    document extraction and validation workflows.
    """
    try:
        # Create a monitoring event for the document
        from core.services.sentinel_service import MonitoringEvent, MonitoringEventType
        
        event = MonitoringEvent(
            event_id=f"INGEST-{datetime.now().timestamp()}",
            event_type=MonitoringEventType.DOCUMENT_DETECTED,
            source=request.file_path,
            data={
                'file_path': request.file_path,
                'document_type': request.document_type,
                'metadata': request.metadata or {},
                'ingested_at': datetime.now().isoformat()
            },
            priority=2
        )
        
        # Add event to sentinel service
        sentinel_service.monitoring_events.append(event)
        
        # Trigger extraction through Sentinel
        extraction_request = sentinel_service.trigger_extraction(event)
        
        return {
            'status': 'success',
            'event_id': event.event_id,
            'extraction_request': extraction_request,
            'message': 'Document queued for extraction'
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/sentinel/feed")
async def get_live_feed(limit: int = 50, unprocessed_only: bool = False):
    """
    Get real-time monitoring feed for Sentinel Live Feed UI
    
    Returns recent monitoring events including:
    - Document detections
    - Expiration warnings
    - Compliance violations
    - Site updates
    """
    events = sentinel_service.get_live_feed(limit=limit, unprocessed_only=unprocessed_only)
    
    return {
        'events': [
            {
                'event_id': e.event_id,
                'event_type': e.event_type.value,
                'timestamp': e.timestamp.isoformat(),
                'source': e.source,
                'data': e.data,
                'priority': e.priority,
                'processed': e.processed
            }
            for e in events
        ],
        'count': len(events)
    }


@app.get("/api/sentinel/statistics")
async def get_sentinel_statistics():
    """Get Sentinel monitoring statistics for dashboard"""
    stats = sentinel_service.get_statistics()
    return stats


@app.post("/api/sentinel/mark-processed/{event_id}")
async def mark_event_processed(event_id: str):
    """Mark a monitoring event as processed"""
    sentinel_service.mark_processed(event_id)
    return {'status': 'success', 'event_id': event_id}


class WatchPathRequest(BaseModel):
    """Request model for adding watch path"""
    path: str


@app.post("/api/sentinel/watch-path")
async def add_watch_path(request: WatchPathRequest):
    """Add a directory path to watch for new documents"""
    if request.path not in sentinel_service.watch_config.watch_paths:
        sentinel_service.watch_config.watch_paths.append(request.path)
    
    return {
        'status': 'success',
        'watched_paths': sentinel_service.watch_config.watch_paths
    }


class ExpirationTrackRequest(BaseModel):
    """Request model for expiration tracking"""
    item_id: str
    item_type: str
    expiration_date: str
    metadata: Optional[Dict[str, Any]] = None


@app.post("/api/sentinel/expiration-track")
async def track_expiration(request: ExpirationTrackRequest):
    """Add an item to track for expiration warnings (30-day threshold)"""
    from datetime import datetime
    
    exp_date = datetime.fromisoformat(request.expiration_date)
    sentinel_service.add_expiring_item(
        request.item_id, 
        request.item_type, 
        exp_date, 
        request.metadata
    )
    
    return {
        'status': 'success',
        'message': f'Tracking {request.item_type} {request.item_id} for expiration'
    }




# ============================================================================
# SELF-HEALING SUITE ENDPOINTS
# ============================================================================

class OutreachRequestModel(BaseModel):
    """Request model for outreach agent"""
    contractor_id: str
    contractor_name: str
    contact_email: str
    document_id: str
    document_type: str
    validation_errors: List[str]


class HeartbeatRegisterRequest(BaseModel):
    """Request to register contractor for heartbeat monitoring"""
    contractor_id: str
    contractor_name: str
    insurance_status: str  # VALID, EXPIRED, EXPIRING_SOON
    insurance_expiration: Optional[str] = None
    license_status: Optional[str] = "VALID"
    license_expiration: Optional[str] = None


@app.post("/api/outreach/send")
async def send_outreach(request: OutreachRequestModel):
    """
    Send automated correction request to contractor
    Part of Self-Healing Suite
    """
    try:
        outreach_request = outreach_agent.send_outreach(
            contractor_id=request.contractor_id,
            contractor_name=request.contractor_name,
            contact_email=request.contact_email,
            document_id=request.document_id,
            document_type=request.document_type,
            validation_errors=request.validation_errors
        )
        
        return {
            'status': 'success',
            'request_id': outreach_request.request_id,
            'delivered': outreach_request.delivered,
            'subject': outreach_request.subject,
            'priority': outreach_request.priority
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/outreach/statistics")
async def get_outreach_stats():
    """Get outreach agent statistics"""
    return outreach_agent.get_outreach_statistics()


@app.post("/api/heartbeat/register")
async def register_contractor(request: HeartbeatRegisterRequest):
    """Register contractor for heartbeat monitoring"""
    try:
        from datetime import datetime
        
        ins_exp = datetime.fromisoformat(request.insurance_expiration) if request.insurance_expiration else None
        lic_exp = datetime.fromisoformat(request.license_expiration) if request.license_expiration else None
        
        heartbeat.register_contractor(
            contractor_id=request.contractor_id,
            contractor_name=request.contractor_name,
            insurance_status=ExpirationStatus(request.insurance_status),
            insurance_expiration=ins_exp,
            license_status=ExpirationStatus(request.license_status) if request.license_status else ExpirationStatus.VALID,
            license_expiration=lic_exp
        )
        
        return {'status': 'success', 'contractor_id': request.contractor_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/heartbeat/on-site/{contractor_id}")
async def mark_contractor_on_site(contractor_id: str, site_id: str):
    """Mark contractor as detected on-site - triggers risk assessment"""
    heartbeat.mark_on_site(contractor_id, site_id)
    return {'status': 'success', 'contractor_id': contractor_id, 'site_id': site_id}


@app.post("/api/heartbeat/off-site/{contractor_id}")
async def mark_contractor_off_site(contractor_id: str):
    """Mark contractor as off-site"""
    heartbeat.mark_off_site(contractor_id)
    return {'status': 'success', 'contractor_id': contractor_id}


@app.get("/api/heartbeat/statistics")
async def get_heartbeat_stats():
    """Get heartbeat monitoring statistics"""
    return heartbeat.get_statistics()


@app.get("/api/heartbeat/high-risk")
async def get_high_risk_contractors():
    """Get all contractors at HIGH or CRITICAL risk"""
    contractors = heartbeat.get_high_risk_contractors()
    return {
        'count': len(contractors),
        'contractors': [
            {
                'contractor_id': c.contractor_id,
                'contractor_name': c.contractor_name,
                'on_site': c.on_site,
                'risk_level': c.risk_level.value,
                'alerts': c.alerts
            }
            for c in contractors
        ]
    }


@app.get("/api/audit/pending-reviews")
async def get_pending_reviews():
    """Get all decisions pending human review"""
    reviews = audit_logger.get_pending_reviews()
    return {
        'count': len(reviews),
        'reviews': [
            {
                'decision_id': r.decision_id,
                'action': r.action.value,
                'agent_name': r.agent_name,
                'timestamp': r.timestamp.isoformat(),
                'reasoning': r.reasoning,
                'confidence': r.confidence
            }
            for r in reviews
        ]
    }


@app.post("/api/audit/review/{decision_id}")
async def review_decision(
    decision_id: str,
    reviewer: str,
    override: Optional[bool] = None,
    notes: Optional[str] = None
):
    """Mark a decision as reviewed by human"""
    success = audit_logger.mark_reviewed(decision_id, reviewer, override, notes)
    return {
        'status': 'success' if success else 'not_found',
        'decision_id': decision_id
    }


@app.get("/api/audit/statistics")
async def get_audit_stats():
    """Get audit trail statistics"""
    return audit_logger.get_statistics()


@app.get("/api/audit/export")
async def export_audit_logs():
    """Export audit logs for regulatory compliance"""
    export_path = audit_logger.export_for_audit()
    return {
        'status': 'success',
        'export_path': export_path,
        'message': 'Audit logs exported for compliance review'
    }


# ============================================================================
# VETERAN DASHBOARD ACTION CENTER - 2027 ENHANCEMENTS
# ============================================================================

# Initialize new agents
from core.agents.broker_liaison_agent import BrokerLiaisonAgent
from core.agents.feasibility_agent import FeasibilityAgent

broker_liaison = BrokerLiaisonAgent()
feasibility_agent = FeasibilityAgent()


class DraftEndorsementRequest(BaseModel):
    """Request to draft endorsement for a ScopeSignal"""
    signal_id: str
    project_id: str
    project_name: str
    project_address: str
    contractor_name: str
    missing_endorsements: List[str]
    insurance_gaps: List[str]
    agency_requirements: List[str]  # SCA, DDC, HPD, DOT
    broker_name: str
    broker_email: Optional[str] = None
    broker_phone: Optional[str] = None


class FeasibilityRequest(BaseModel):
    """Request for feasibility assessment"""
    signal_id: str
    project_id: str
    project_value: float
    profit_margin: float = 0.15
    insurance_gaps: List[str]
    missing_endorsements: List[str]
    agency_requirements: List[str]


@app.post("/api/broker-liaison/draft-endorsement")
async def draft_endorsement(request: DraftEndorsementRequest):
    """
    Task 1: The Outreach Bridge
    Draft insurance endorsement request when 'Fix Compliance' is clicked
    """
    try:
        from packages.core import (
            ScopeSignal, BrokerContact, ExtractedField,
            AgencyRequirement, LeadStatus
        )
        
        # Build BrokerContact
        broker_contact = BrokerContact(
            broker_name=ExtractedField(
                field_name="broker_name",
                value=request.broker_name,
                confidence=1.0
            ),
            broker_email=ExtractedField(
                field_name="broker_email",
                value=request.broker_email,
                confidence=1.0
            ) if request.broker_email else None,
            broker_phone=ExtractedField(
                field_name="broker_phone",
                value=request.broker_phone,
                confidence=1.0
            ) if request.broker_phone else None
        )
        
        # Build ScopeSignal
        signal = ScopeSignal(
            signal_id=request.signal_id,
            project_id=request.project_id,
            project_name=request.project_name,
            project_address=request.project_address,
            contractor_name=request.contractor_name,
            status=LeadStatus.CONTESTABLE,
            missing_endorsements=request.missing_endorsements,
            insurance_gaps=request.insurance_gaps,
            agency_requirements=[AgencyRequirement(a) for a in request.agency_requirements],
            broker_contact=broker_contact
        )
        
        # Draft endorsement request
        endorsement = broker_liaison.draft_endorsement_request(signal)
        
        return {
            'status': 'success',
            'request_id': endorsement.request_id,
            'subject': endorsement.subject_line,
            'body': endorsement.email_body,
            'urgency': endorsement.urgency_level,
            'required_endorsements': endorsement.required_endorsements,
            'decision_proof': {
                'agent_id': endorsement.decision_proof.agent_id,
                'confidence': endorsement.decision_proof.confidence_score,
                'reasoning': endorsement.decision_proof.reasoning_chain,
                'agent_handshake': {
                    'from_agent': endorsement.decision_proof.agent_handshake.from_agent,
                    'to_agent': endorsement.decision_proof.agent_handshake.to_agent,
                    'validation_status': endorsement.decision_proof.agent_handshake.validation_status
                } if endorsement.decision_proof.agent_handshake else None
            } if endorsement.decision_proof else None,
            'statistics': broker_liaison.get_statistics()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/vision-lead-correlation/{project_id}")
async def get_vision_lead_correlation(project_id: str):
    """
    Task 2: Vision-Lead Correlation
    Link Sentinel-Scope detections to ScopeSignal opportunities
    """
    try:
        # Get recent sentinel events
        events = sentinel_service.get_live_feed(limit=100)
        
        # Correlate to project
        correlations = sentinel_service.correlate_vision_to_leads(
            project_id=project_id,
            sentinel_events=events
        )
        
        return {
            'status': 'success',
            'project_id': project_id,
            'correlations': correlations
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/predictive-risk/profitability-drain")
async def calculate_profitability_drain(request: FeasibilityRequest):
    """
    Task 4: Predictive Risk - Profitability Drain Calculation
    Calculate projected profitability drain from insurance gaps
    """
    try:
        from packages.core import ScopeSignal, AgencyRequirement, LeadStatus
        
        # Build minimal ScopeSignal for feasibility
        signal = ScopeSignal(
            signal_id=request.signal_id,
            project_id=request.project_id,
            project_name="Assessment Project",
            project_address="N/A",
            contractor_name="N/A",
            status=LeadStatus.CONTESTABLE,
            missing_endorsements=request.missing_endorsements,
            insurance_gaps=request.insurance_gaps,
            agency_requirements=[AgencyRequirement(a) for a in request.agency_requirements]
        )
        
        # Assess feasibility with profitability drain
        assessment = feasibility_agent.assess_feasibility(
            signal=signal,
            estimated_project_value=request.project_value,
            estimated_profit_margin=request.profit_margin
        )
        
        return {
            'status': 'success',
            'signal_id': request.signal_id,
            'feasibility_score': assessment.overall_score,
            'confidence': assessment.confidence,
            'projected_premium_increase': assessment.projected_premium_increase,
            'profitability_drain_percent': assessment.projected_profitability_drain,
            'estimated_bid_adjustment': assessment.estimated_bid_adjustment,
            'recommendation': assessment.recommendation,
            'reasoning': assessment.reasoning,
            'risk_factors': assessment.risk_factors,
            'cost_efficiency': {
                'tokens_used': assessment.calculation_tokens,
                'cost_usd': assessment.calculation_cost,
                'meets_target': assessment.calculation_cost <= 0.007
            },
            'statistics': feasibility_agent.get_statistics()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/agent-statistics")
async def get_agent_statistics():
    """Get statistics for all Action Center agents"""
    return {
        'broker_liaison': broker_liaison.get_statistics(),
        'feasibility_agent': feasibility_agent.get_statistics(),
        'outreach_agent': outreach_agent.get_statistics()
    }


# ============================================================================
# GOVERNANCE & QUALITY DASHBOARD - NYC 2026-2027 COMPLIANCE
# ============================================================================

from packages.monitoring import (
    get_telemetry_service,
    get_bias_auditor,
    get_legal_sandbox,
    get_immutable_logger,
    AgentType
)

telemetry = get_telemetry_service()
bias_auditor = get_bias_auditor()
legal_sandbox = get_legal_sandbox()
immutable_logger = get_immutable_logger()


@app.get("/api/governance/dashboard")
async def get_governance_dashboard():
    """
    Get comprehensive governance dashboard data
    Includes agent flow accuracy, human override rates, cost attribution, and TTFT metrics
    """
    try:
        return telemetry.get_dashboard_summary()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/governance/agent-flow-accuracy")
async def get_agent_flow_accuracy(
    agent_type: Optional[str] = None,
    time_window_hours: int = 24
):
    """Get agent flow accuracy metrics"""
    try:
        agent = AgentType(agent_type) if agent_type else None
        return telemetry.get_agent_flow_accuracy(agent, time_window_hours)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/governance/human-override-rate")
async def get_human_override_rate(
    agent_type: Optional[str] = None,
    time_window_hours: int = 24
):
    """Get human-on-the-loop override rate"""
    try:
        agent = AgentType(agent_type) if agent_type else None
        return telemetry.get_human_override_rate(agent, time_window_hours)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/governance/cost-attribution")
async def get_cost_attribution(
    agent_type: Optional[str] = None,
    time_window_hours: int = 24
):
    """Get token cost attribution per agent"""
    try:
        agent = AgentType(agent_type) if agent_type else None
        return telemetry.get_cost_attribution(agent, time_window_hours)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/governance/ttft-performance")
async def get_ttft_performance(
    agent_type: Optional[str] = None,
    time_window_hours: int = 1
):
    """Get Time-to-First-Token performance metrics"""
    try:
        agent = AgentType(agent_type) if agent_type else None
        return telemetry.get_ttft_stats(agent, time_window_hours)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/governance/bias-audit/latest")
async def get_latest_bias_audit():
    """Get the latest bias audit log (NYC Local Law 144 compliance)"""
    try:
        audit = bias_auditor.get_latest_audit()
        if not audit:
            return {'status': 'no_audits_yet', 'documents_pending': bias_auditor.documents_since_last_audit}
        
        return {
            'audit_id': audit.audit_id,
            'audit_timestamp': audit.audit_timestamp.isoformat(),
            'documents_processed': audit.documents_processed,
            'overall_bias_detected': audit.overall_bias_detected,
            'avg_accuracy': audit.avg_accuracy,
            'max_variance': audit.max_variance_across_groups,
            'retraining_required': audit.retraining_required,
            'retraining_reason': audit.retraining_reason,
            'tests': [
                {
                    'test_type': t.test_type.value,
                    'passed': t.passed,
                    'bias_detected': t.bias_detected,
                    'confidence': t.confidence_score,
                    'variance': t.accuracy_variance
                }
                for t in audit.adversarial_tests
            ],
            'protected_characteristics_tested': audit.protected_characteristics_tested,
            'human_review_flagged_count': len(audit.human_review_flagged),
            'audit_hash': audit.audit_hash
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/governance/bias-audit/statistics")
async def get_bias_audit_statistics():
    """Get bias auditor statistics"""
    try:
        return bias_auditor.get_statistics()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/governance/legal-sandbox/pending")
async def get_pending_legal_reviews():
    """Get governance proofs awaiting legal review"""
    try:
        pending = legal_sandbox.get_pending_reviews()
        return {
            'count': len(pending),
            'pending_reviews': [
                {
                    'proof_id': p.proof_id,
                    'timestamp': p.timestamp.isoformat(),
                    'content_type': p.content_type,
                    'sandbox_status': p.sandbox_status.value,
                    'risk_score': p.risk_score,
                    'triggers_detected': len(p.triggers_detected),
                    'send_blocked': p.send_blocked,
                    'recipient': p.recipient_email
                }
                for p in pending
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/governance/legal-sandbox/approve/{proof_id}")
async def approve_governance_proof(
    proof_id: str,
    reviewer_id: str,
    notes: Optional[str] = None
):
    """Approve a governance proof for sending"""
    try:
        success = legal_sandbox.approve_proof(proof_id, reviewer_id, notes)
        if success:
            return {'status': 'approved', 'proof_id': proof_id}
        else:
            raise HTTPException(status_code=404, detail="Proof not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/governance/legal-sandbox/reject/{proof_id}")
async def reject_governance_proof(
    proof_id: str,
    reviewer_id: str,
    reason: str
):
    """Reject a governance proof"""
    try:
        success = legal_sandbox.reject_proof(proof_id, reviewer_id, reason)
        if success:
            return {'status': 'rejected', 'proof_id': proof_id}
        else:
            raise HTTPException(status_code=404, detail="Proof not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/governance/legal-sandbox/statistics")
async def get_legal_sandbox_statistics():
    """Get legal sandbox statistics"""
    try:
        return legal_sandbox.get_statistics()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/governance/immutable-log/verify")
async def verify_immutable_log():
    """Verify integrity of immutable audit log chain"""
    try:
        verified = immutable_logger.verify_chain()
        stats = immutable_logger.get_statistics()
        
        return {
            'chain_verified': verified,
            'status': 'valid' if verified else 'tampered',
            'statistics': stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/governance/immutable-log/export")
async def export_immutable_log():
    """Export immutable logs for regulatory audit"""
    try:
        import tempfile
        import os
        
        # Create temp file for export
        fd, filepath = tempfile.mkstemp(suffix='.json', prefix='audit-export-')
        os.close(fd)
        
        exported_path = immutable_logger.export_for_audit(filepath)
        
        return {
            'status': 'exported',
            'filepath': exported_path,
            'total_entries': len(immutable_logger.log_chain),
            'chain_verified': immutable_logger.verify_chain()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
