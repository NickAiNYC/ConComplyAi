"""
SentinelService - Real-time monitoring and ingestion service
Integrated from Sentinel-Scope into ConComplyAi Core

Features:
- File system watching for new documents
- Real-time site monitoring alerts
- Unified ingestion triggering for extraction agents
- Expiration tracking and notifications
"""
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime, timedelta
from pathlib import Path
import asyncio
from enum import Enum
from pydantic import BaseModel, Field


class MonitoringEventType(str, Enum):
    """Types of monitoring events"""
    DOCUMENT_DETECTED = "DOCUMENT_DETECTED"
    EXPIRATION_WARNING = "EXPIRATION_WARNING"
    COMPLIANCE_VIOLATION = "COMPLIANCE_VIOLATION"
    SITE_UPDATE = "SITE_UPDATE"


class MonitoringEvent(BaseModel):
    """Single monitoring event from Sentinel"""
    event_id: str
    event_type: MonitoringEventType
    timestamp: datetime = Field(default_factory=datetime.now)
    source: str  # File path, site ID, etc.
    data: Dict[str, Any]
    priority: int = Field(ge=1, le=5, default=3)  # 1=critical, 5=info
    processed: bool = Field(default=False)


class WatchConfig(BaseModel):
    """Configuration for file system watching"""
    watch_paths: List[str] = Field(default_factory=list)
    file_patterns: List[str] = Field(default_factory=lambda: ["*.pdf", "*.jpg", "*.png"])
    poll_interval_seconds: int = Field(default=5, ge=1)
    auto_trigger_extraction: bool = Field(default=True)


class SentinelService:
    """
    Unified monitoring service that watches for compliance events
    and triggers ConComplyAi extraction agents
    """
    
    def __init__(self, watch_config: Optional[WatchConfig] = None):
        self.watch_config = watch_config or WatchConfig()
        self.monitoring_events: List[MonitoringEvent] = []
        self.is_monitoring = False
        self._callbacks: List[Callable] = []
        self._expiring_items: List[Dict[str, Any]] = []
        
    def register_callback(self, callback: Callable[[MonitoringEvent], None]):
        """Register a callback to be invoked when new events are detected"""
        self._callbacks.append(callback)
        
    def add_expiring_item(self, item_id: str, item_type: str, 
                         expiration_date: datetime, metadata: Dict[str, Any] = None):
        """Add an item to track for expiration warnings"""
        self._expiring_items.append({
            'item_id': item_id,
            'item_type': item_type,
            'expiration_date': expiration_date,
            'metadata': metadata or {}
        })
        
    def check_expirations(self) -> List[MonitoringEvent]:
        """Check for items expiring soon (within 30 days)"""
        now = datetime.now()
        warning_threshold = now + timedelta(days=30)
        events = []
        
        for item in self._expiring_items:
            exp_date = item['expiration_date']
            if now <= exp_date <= warning_threshold:
                days_until = (exp_date - now).days
                event = MonitoringEvent(
                    event_id=f"EXP-{item['item_id']}-{now.timestamp()}",
                    event_type=MonitoringEventType.EXPIRATION_WARNING,
                    source=item['item_id'],
                    data={
                        'item_type': item['item_type'],
                        'expiration_date': exp_date.isoformat(),
                        'days_until_expiration': days_until,
                        **item['metadata']
                    },
                    priority=1 if days_until <= 7 else 2
                )
                events.append(event)
                self._emit_event(event)
                
        return events
    
    def watch_directory(self, path: str) -> List[MonitoringEvent]:
        """
        Watch a directory for new files matching patterns
        Returns list of newly detected files
        """
        events = []
        path_obj = Path(path)
        
        if not path_obj.exists():
            return events
            
        for pattern in self.watch_config.file_patterns:
            for file_path in path_obj.glob(pattern):
                if self._is_new_file(file_path):
                    event = MonitoringEvent(
                        event_id=f"DOC-{file_path.stem}-{datetime.now().timestamp()}",
                        event_type=MonitoringEventType.DOCUMENT_DETECTED,
                        source=str(file_path),
                        data={
                            'file_name': file_path.name,
                            'file_size': file_path.stat().st_size,
                            'file_type': file_path.suffix,
                            'detected_at': datetime.now().isoformat()
                        },
                        priority=2
                    )
                    events.append(event)
                    self._emit_event(event)
                    
        return events
    
    def report_compliance_event(self, site_id: str, violation_data: Dict[str, Any]):
        """Report a compliance violation or update from site monitoring"""
        event = MonitoringEvent(
            event_id=f"COMP-{site_id}-{datetime.now().timestamp()}",
            event_type=MonitoringEventType.COMPLIANCE_VIOLATION,
            source=site_id,
            data=violation_data,
            priority=violation_data.get('risk_level', 3)
        )
        self._emit_event(event)
        return event
    
    def get_live_feed(self, limit: int = 50, unprocessed_only: bool = False) -> List[MonitoringEvent]:
        """
        Get recent monitoring events for live feed display
        
        Args:
            limit: Maximum number of events to return
            unprocessed_only: Only return unprocessed events
        """
        events = self.monitoring_events
        
        if unprocessed_only:
            events = [e for e in events if not e.processed]
            
        # Sort by timestamp descending (most recent first)
        events = sorted(events, key=lambda e: e.timestamp, reverse=True)
        
        return events[:limit]
    
    def mark_processed(self, event_id: str):
        """Mark an event as processed"""
        for event in self.monitoring_events:
            if event.event_id == event_id:
                event.processed = True
                break
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get monitoring statistics for dashboard"""
        total_events = len(self.monitoring_events)
        unprocessed = len([e for e in self.monitoring_events if not e.processed])
        
        by_type = {}
        for event in self.monitoring_events:
            event_type = event.event_type.value
            by_type[event_type] = by_type.get(event_type, 0) + 1
            
        critical_count = len([e for e in self.monitoring_events if e.priority == 1])
        
        return {
            'total_events': total_events,
            'unprocessed_events': unprocessed,
            'critical_events': critical_count,
            'events_by_type': by_type,
            'monitoring_active': self.is_monitoring,
            'watched_paths': self.watch_config.watch_paths
        }
    
    async def start_monitoring(self):
        """Start continuous monitoring (async)"""
        self.is_monitoring = True
        
        while self.is_monitoring:
            # Check all watched directories
            for path in self.watch_config.watch_paths:
                self.watch_directory(path)
            
            # Check for expiring items
            self.check_expirations()
            
            # Wait for next poll interval
            await asyncio.sleep(self.watch_config.poll_interval_seconds)
    
    def stop_monitoring(self):
        """Stop continuous monitoring"""
        self.is_monitoring = False
    
    def _is_new_file(self, file_path: Path) -> bool:
        """Check if file is new (not already in events)"""
        file_str = str(file_path)
        return not any(e.source == file_str for e in self.monitoring_events)
    
    def _emit_event(self, event: MonitoringEvent):
        """Emit event to all registered callbacks"""
        self.monitoring_events.append(event)
        
        for callback in self._callbacks:
            try:
                callback(event)
            except Exception as e:
                print(f"Error in callback: {e}")
    
    def trigger_extraction(self, event: MonitoringEvent) -> Dict[str, Any]:
        """
        Trigger ConComplyAi extraction agents for a document event
        This is the unified ingestion point
        """
        if event.event_type != MonitoringEventType.DOCUMENT_DETECTED:
            return {'error': 'Event type must be DOCUMENT_DETECTED'}
        
        # Extract file information
        file_path = event.source
        file_data = event.data
        
        # Prepare extraction request
        extraction_request = {
            'document_id': event.event_id,
            'file_path': file_path,
            'file_name': file_data.get('file_name'),
            'detected_at': event.timestamp.isoformat(),
            'trigger_source': 'sentinel_monitoring',
            'auto_triggered': self.watch_config.auto_trigger_extraction
        }
        
        return extraction_request
    
    def correlate_vision_to_leads(
        self,
        project_id: str,
        sentinel_events: List[MonitoringEvent]
    ) -> Dict[str, Any]:
        """
        Task 2: Vision-Lead Correlation
        Link Sentinel-Scope detections to ScopeSignal opportunities.
        
        Args:
            project_id: Project to check for correlations
            sentinel_events: Recent Sentinel detection events
            
        Returns:
            Correlation results with matched leads
        """
        from packages.core import ScopeSignal, LeadStatus
        
        correlations = []
        
        for event in sentinel_events:
            # Check if this is a vision detection event
            if event.event_type == MonitoringEventType.COMPLIANCE_VIOLATION:
                # Check if we have a CONTESTABLE lead for this project
                if event.data.get('project_id') == project_id:
                    correlation = {
                        'sentinel_event_id': event.event_id,
                        'project_id': project_id,
                        'event_type': event.event_type.value,
                        'detection_timestamp': event.timestamp.isoformat(),
                        'is_contestable': event.data.get('status') == 'CONTESTABLE',
                        'priority': event.priority,
                        'site_status_memo_generated': False
                    }
                    
                    # If CONTESTABLE, generate site status memo
                    if correlation['is_contestable']:
                        memo = self._generate_site_status_memo(
                            project_id,
                            event
                        )
                        correlation['site_status_memo'] = memo
                        correlation['site_status_memo_generated'] = True
                    
                    correlations.append(correlation)
        
        return {
            'project_id': project_id,
            'total_correlations': len(correlations),
            'contestable_leads': len([c for c in correlations if c.get('is_contestable')]),
            'correlations': correlations
        }
    
    def _generate_site_status_memo(
        self,
        project_id: str,
        detection_event: MonitoringEvent
    ) -> str:
        """
        Auto-generate a Site Status Memo for estimator
        when a CONTESTABLE lead appears for a monitored project.
        """
        event_data = detection_event.data
        
        memo = f"""SITE STATUS MEMO
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Project ID: {project_id}
Status: CONTESTABLE OPPORTUNITY DETECTED

DETECTION SUMMARY:
- Detection ID: {detection_event.event_id}
- Detection Time: {detection_event.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
- Priority Level: {detection_event.priority}/5
- Source: Sentinel-Scope Vision Monitoring

COMPLIANCE FINDINGS:
{self._format_event_data(event_data)}

OPPORTUNITY ASSESSMENT:
This project is currently under active Sentinel-Scope monitoring and has been 
flagged as a CONTESTABLE opportunity based on detected compliance gaps.

ESTIMATOR ACTION ITEMS:
1. Review compliance findings above
2. Assess current contractor's remediation status
3. Evaluate opportunity to offer compliance consultation
4. Consider proactive outreach if gaps persist
5. Update project watchlist priority

RISK INDICATORS:
- Active Monitoring: Yes
- Compliance Gaps Detected: {event_data.get('gap_count', 'Multiple')}
- Estimated Remediation Cost: {event_data.get('estimated_cost', 'TBD')}
- Recommended Follow-up: {event_data.get('follow_up_days', '7')} days

NEXT STEPS:
Contact project manager to discuss compliance consultation proposal.
Use BrokerLiaison agent to draft insurance endorsement requests if needed.

---
Auto-generated by Sentinel-Scope Vision-Lead Correlation System
Cost: $0.001 per memo generation
"""
        
        return memo
    
    def _format_event_data(self, data: Dict[str, Any]) -> str:
        """Format event data for memo."""
        formatted = []
        for key, value in data.items():
            if key not in ['project_id', 'status']:
                formatted.append(f"- {key.replace('_', ' ').title()}: {value}")
        
        return '\n'.join(formatted) if formatted else "- No additional details available"
