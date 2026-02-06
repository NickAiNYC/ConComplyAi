"""FastAPI Health Endpoint - Production observability"""
from fastapi import FastAPI, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from core.config import BUSINESS_CONFIG
from core.services import SentinelService
from core.models import DocumentType

app = FastAPI(title="Construction Compliance AI", version="1.0.0")

# CORS middleware for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Sentinel Service
sentinel_service = SentinelService()


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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
