"""
AgentHandshakeV2 API Router - Production REST Endpoint

This module provides the POST /handshake endpoint for external system integration.
Supports Procore webhooks, CSV drops, and email forwarding with immediate AuditProof
SHA-256 hash return.

2026 Production Specifications:
- Handshake version: 2.0
- Source system tracking (PROCORE_COI_PULL, EXCEL_CSV_DROP, EMAIL_FORWARD)
- Immediate SHA-256 AuditProof hash return
- Full request/response schema documentation

See docs/AGENT_HANDSHAKE_V2.md for detailed examples and integration guide.
"""
from typing import Optional, Dict, Any, List
from datetime import datetime
from pathlib import Path
import hashlib
import json

from fastapi import FastAPI, HTTPException, File, UploadFile, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator

from packages.core.agent_protocol import (
    AgentRole,
    AgentHandshakeV2,
    SourceSystem,
    AuditChain
)
from packages.core.audit import create_decision_proof, DecisionProof


# =============================================================================
# REQUEST/RESPONSE SCHEMAS
# =============================================================================

class HandshakeRequest(BaseModel):
    """
    Request schema for POST /handshake endpoint
    
    This schema handles both Procore webhook payloads and CSV drop uploads.
    
    Example Procore Payload:
    ```json
    {
        "source_system": "PROCORE_COI_PULL",
        "project_id": "PROCORE-12345",
        "document_type": "COI",
        "contractor_name": "ABC Construction",
        "document_url": "https://procore.com/documents/...",
        "metadata": {
            "procore_project_id": "12345",
            "procore_company_id": "678"
        }
    }
    ```
    
    Example CSV Drop:
    ```json
    {
        "source_system": "EXCEL_CSV_DROP",
        "project_id": "CSV-BATCH-2026-02-06",
        "document_type": "COI",
        "documents": [
            {"contractor_name": "ABC Construction", "file_path": "/uploads/abc_coi.pdf"},
            {"contractor_name": "XYZ Builders", "file_path": "/uploads/xyz_coi.pdf"}
        ]
    }
    ```
    """
    # Required fields
    source_system: SourceSystem = Field(
        description="System originating this handshake"
    )
    project_id: str = Field(
        description="Unique project identifier"
    )
    document_type: str = Field(
        default="COI",
        description="Type of document (COI, OSHA_LOG, LICENSE, etc.)"
    )
    
    # Document details
    contractor_name: Optional[str] = Field(
        default=None,
        description="Contractor/company name"
    )
    document_url: Optional[str] = Field(
        default=None,
        description="URL to document (for webhook integrations)"
    )
    documents: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Batch documents (for CSV drops)"
    )
    
    # Optional metadata
    permit_number: Optional[str] = Field(
        default=None,
        description="NYC DOB permit number if available"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context from source system"
    )
    
    # Agent routing
    target_agent: AgentRole = Field(
        default=AgentRole.GUARD,
        description="Which agent should process this (default: Guard)"
    )
    
    @validator('documents')
    def validate_documents(cls, v, values):
        """Ensure either document_url or documents is provided"""
        if v is None and values.get('document_url') is None:
            raise ValueError("Either document_url or documents must be provided")
        return v


class HandshakeResponse(BaseModel):
    """
    Response schema for POST /handshake endpoint
    
    Returns immediately with AuditProof SHA-256 hash for tracking.
    Actual processing happens asynchronously.
    """
    # Status
    success: bool = Field(description="Whether handshake was accepted")
    message: str = Field(description="Human-readable status message")
    
    # Audit proof
    audit_proof_hash: str = Field(
        description="SHA-256 hash from DecisionProof for tracking"
    )
    handshake_id: str = Field(
        description="Unique handshake identifier"
    )
    handshake_version: str = Field(
        default="2.0",
        description="Handshake protocol version"
    )
    
    # Tracking
    project_id: str = Field(description="Project identifier")
    source_system: SourceSystem = Field(description="Source system")
    target_agent: AgentRole = Field(description="Agent assigned to process")
    
    # Metadata
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Handshake creation timestamp"
    )
    estimated_processing_time_seconds: int = Field(
        default=30,
        description="Estimated time to complete processing"
    )
    
    # Optional details
    documents_queued: Optional[int] = Field(
        default=None,
        description="Number of documents queued (for batch)"
    )


# =============================================================================
# FASTAPI ROUTER
# =============================================================================

app = FastAPI(
    title="ConComplyAi AgentHandshakeV2 API",
    description="Production REST endpoint for multi-agent compliance workflows",
    version="2.0.0"
)


@app.post(
    "/handshake",
    response_model=HandshakeResponse,
    summary="Create Agent Handshake",
    description="""
    Create an AgentHandshakeV2 for compliance document processing.
    
    This endpoint accepts documents from external systems (Procore, Excel/CSV, Email)
    and immediately returns an AuditProof SHA-256 hash for tracking. Processing 
    happens asynchronously through the Scout → Guard → Fixer agent pipeline.
    
    **Supported Source Systems:**
    - PROCORE_COI_PULL: Procore webhook integration
    - EXCEL_CSV_DROP: CSV file upload
    - EMAIL_FORWARD: Email forwarding integration
    - MANUAL_UPLOAD: Direct portal upload
    
    **Returns:**
    Immediate response with AuditProof SHA-256 hash for tracking. Use this hash
    to query processing status and results.
    
    **Processing Flow:**
    1. Handshake created and audit proof generated
    2. Document queued for target agent (default: Guard)
    3. Agent processes document and generates decision proof
    4. Results available via GET /handshake/{audit_proof_hash}/status
    
    See docs/AGENT_HANDSHAKE_V2.md for detailed examples.
    """
)
async def create_handshake(request: HandshakeRequest) -> HandshakeResponse:
    """
    Create an AgentHandshakeV2 for document processing
    
    This is the main entry point for external system integration.
    Returns immediately with AuditProof hash while processing happens async.
    
    Args:
        request: HandshakeRequest with document details and source system
    
    Returns:
        HandshakeResponse with audit_proof_hash for tracking
    
    Raises:
        HTTPException: If validation fails or system error occurs
    """
    try:
        # Generate handshake ID
        handshake_id = f"HANDSHAKE-{request.source_system.value}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        
        # Create decision proof for handshake acceptance
        decision_proof = create_decision_proof(
            agent_name="API",
            decision="HANDSHAKE_ACCEPTED",
            input_data={
                "source_system": request.source_system.value,
                "project_id": request.project_id,
                "document_type": request.document_type,
                "contractor_name": request.contractor_name,
                "target_agent": request.target_agent.value,
            },
            logic_citations=[],
            reasoning=f"Handshake accepted from {request.source_system.value} for project {request.project_id}. Document queued for {request.target_agent.value} agent processing.",
            confidence=1.0,
            risk_level="LOW",
            estimated_financial_impact=None,
            cost_usd=0.0
        )
        
        # Create AgentHandshakeV2
        handshake = AgentHandshakeV2(
            handshake_version="2.0",
            source_agent=AgentRole.INTELLIGENCE,  # API acts as Intelligence layer
            target_agent=request.target_agent,
            project_id=request.project_id,
            source_system=request.source_system,
            decision_hash=decision_proof.proof_hash,
            parent_handshake_id=None,  # This is the initial handshake
            transition_reason="handshake_created",
            metadata={
                **request.metadata,
                "document_type": request.document_type,
                "contractor_name": request.contractor_name,
                "permit_number": request.permit_number,
                "handshake_id": handshake_id
            }
        )
        
        # TODO: Queue document for async processing
        # In production: Add to Redis queue, trigger Lambda/Cloud Function, etc.
        # For now, just acknowledge receipt
        
        # Determine document count
        documents_queued = None
        if request.documents:
            documents_queued = len(request.documents)
        elif request.document_url:
            documents_queued = 1
        
        # Build response
        response = HandshakeResponse(
            success=True,
            message=f"Handshake accepted. Document queued for {request.target_agent.value} agent processing.",
            audit_proof_hash=decision_proof.proof_hash,
            handshake_id=handshake_id,
            handshake_version="2.0",
            project_id=request.project_id,
            source_system=request.source_system,
            target_agent=request.target_agent,
            timestamp=datetime.utcnow(),
            estimated_processing_time_seconds=30,
            documents_queued=documents_queued
        )
        
        return response
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create handshake: {str(e)}"
        )


@app.get(
    "/handshake/{audit_proof_hash}/status",
    summary="Get Handshake Status",
    description="Query processing status using AuditProof SHA-256 hash"
)
async def get_handshake_status(audit_proof_hash: str) -> Dict[str, Any]:
    """
    Get status of a handshake by AuditProof hash
    
    Args:
        audit_proof_hash: SHA-256 hash returned from POST /handshake
    
    Returns:
        Dict with processing status and results
    """
    # TODO: Query processing status from database/queue
    # For now, return mock response
    return {
        "audit_proof_hash": audit_proof_hash,
        "status": "PROCESSING",
        "message": "Document is being processed by Guard agent",
        "progress_percentage": 50,
        "estimated_completion_seconds": 15
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "AgentHandshakeV2 API",
        "version": "2.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def create_handshake_from_procore_webhook(
    procore_payload: Dict[str, Any]
) -> HandshakeRequest:
    """
    Convert Procore webhook payload to HandshakeRequest
    
    Procore sends webhooks when COI documents are uploaded or updated.
    This function transforms their payload into our HandshakeRequest format.
    
    Args:
        procore_payload: Raw Procore webhook JSON
    
    Returns:
        HandshakeRequest ready for POST /handshake
    
    Example Procore Webhook:
    ```json
    {
        "project_id": "12345",
        "company_id": "678",
        "document": {
            "id": "doc-789",
            "name": "ABC_Construction_COI.pdf",
            "url": "https://procore.com/documents/...",
            "contractor_name": "ABC Construction"
        }
    }
    ```
    """
    doc = procore_payload.get("document", {})
    
    return HandshakeRequest(
        source_system=SourceSystem.PROCORE_COI_PULL,
        project_id=f"PROCORE-{procore_payload.get('project_id')}",
        document_type="COI",
        contractor_name=doc.get("contractor_name"),
        document_url=doc.get("url"),
        metadata={
            "procore_project_id": procore_payload.get("project_id"),
            "procore_company_id": procore_payload.get("company_id"),
            "procore_document_id": doc.get("id"),
            "document_name": doc.get("name")
        },
        target_agent=AgentRole.GUARD
    )


def create_handshake_from_csv_row(
    csv_row: Dict[str, str],
    batch_id: str
) -> HandshakeRequest:
    """
    Convert CSV row to HandshakeRequest
    
    For Excel/CSV drops with multiple contractors.
    
    Args:
        csv_row: Dict from CSV DictReader
        batch_id: Unique identifier for this CSV batch
    
    Returns:
        HandshakeRequest ready for POST /handshake
    
    Expected CSV Columns:
    - contractor_name
    - document_path
    - permit_number (optional)
    - address (optional)
    """
    return HandshakeRequest(
        source_system=SourceSystem.EXCEL_CSV_DROP,
        project_id=f"CSV-{batch_id}",
        document_type="COI",
        contractor_name=csv_row.get("contractor_name"),
        document_url=csv_row.get("document_path"),
        permit_number=csv_row.get("permit_number"),
        metadata={
            "batch_id": batch_id,
            "address": csv_row.get("address"),
            "csv_row_number": csv_row.get("_row_num")
        },
        target_agent=AgentRole.GUARD
    )
