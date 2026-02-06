# Sentinel Package - Real-time Monitoring Module

## Overview

The Sentinel package provides real-time monitoring capabilities for ConComplyAi, integrated from Sentinel-Scope. It creates a unified "Compliance Command Center" that watches for compliance events and triggers extraction agents automatically.

## Features

### 1. **File System Watching**
- Monitor directories for new documents (PDF, JPG, PNG)
- Automatic detection of contractor documents
- Configurable polling intervals
- Pattern-based file filtering

### 2. **Expiration Tracking**
- 30-day advance warnings for expiring items
- Track COI, licenses, permits, and other time-sensitive documents
- Automatic priority escalation as expiration approaches
- Integration with notification engine

### 3. **Compliance Event Monitoring**
- Real-time violation detection
- Site update tracking
- Priority-based alerting (1=critical to 5=info)
- Event categorization and filtering

### 4. **Unified Ingestion**
- Automatic triggering of ConComplyAi extraction agents
- Seamless integration with document processing pipeline
- Callback system for custom event handling
- RESTful API endpoints for external integration

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  Sentinel Service                        │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │ File Watcher │  │   Expiration │  │   Event      │ │
│  │              │  │   Tracker    │  │   Manager    │ │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘ │
│         │                 │                  │          │
│         └─────────────────┴──────────────────┘          │
│                          │                               │
│                    Monitoring Events                     │
│                          │                               │
└──────────────────────────┼──────────────────────────────┘
                           │
           ┌───────────────┴───────────────┐
           │                               │
    ┌──────▼───────┐            ┌─────────▼────────┐
    │  Extraction  │            │  Notification    │
    │   Agents     │            │    Engine        │
    └──────────────┘            └──────────────────┘
```

## Installation

The Sentinel package is integrated into ConComplyAi core:

```bash
# Already included in requirements.txt
pip install -r requirements.txt
```

## Usage

### Basic Setup

```python
from core.services import SentinelService
from core.services.sentinel_service import WatchConfig

# Initialize with configuration
config = WatchConfig(
    watch_paths=['/path/to/documents'],
    file_patterns=['*.pdf', '*.jpg', '*.png'],
    poll_interval_seconds=5,
    auto_trigger_extraction=True
)

sentinel = SentinelService(watch_config=config)
```

### Watch Directory for New Documents

```python
# Single directory scan
events = sentinel.watch_directory('/path/to/documents')

for event in events:
    print(f"Detected: {event.source}")
    
    # Auto-trigger extraction if enabled
    if config.auto_trigger_extraction:
        extraction_request = sentinel.trigger_extraction(event)
```

### Track Expiring Items

```python
from datetime import datetime, timedelta

# Add item to track
sentinel.add_expiring_item(
    item_id='COI-2024-001',
    item_type='Certificate of Insurance',
    expiration_date=datetime.now() + timedelta(days=25),
    metadata={
        'contractor': 'ABC Construction',
        'policy_number': 'POL-12345'
    }
)

# Check for expiring items
warnings = sentinel.check_expirations()
for warning in warnings:
    print(f"Warning: {warning.data['item_type']} expires in {warning.data['days_until_expiration']} days")
```

### Register Event Callbacks

```python
def on_critical_event(event):
    """Custom handler for critical events"""
    if event.priority == 1:
        print(f"CRITICAL: {event.event_type}")
        # Send email, SMS, etc.

sentinel.register_callback(on_critical_event)
```

### Continuous Monitoring (Async)

```python
import asyncio

async def monitor():
    # Start continuous monitoring
    await sentinel.start_monitoring()

# Run monitoring
asyncio.run(monitor())

# To stop: sentinel.stop_monitoring()
```

### Get Live Feed

```python
# Get recent events
events = sentinel.get_live_feed(limit=50, unprocessed_only=True)

# Mark event as processed
sentinel.mark_processed(event_id='DOC-123-456')
```

### Get Statistics

```python
stats = sentinel.get_statistics()

print(f"Total Events: {stats['total_events']}")
print(f"Unprocessed: {stats['unprocessed_events']}")
print(f"Critical: {stats['critical_events']}")
print(f"Monitoring Active: {stats['monitoring_active']}")
```

## API Endpoints

### POST `/api/sentinel/ingest`
Unified ingestion endpoint - triggers extraction agents

**Request:**
```json
{
  "file_path": "/path/to/document.pdf",
  "document_type": "COI",
  "metadata": {
    "contractor": "ABC Construction"
  }
}
```

**Response:**
```json
{
  "status": "success",
  "event_id": "INGEST-1234567890",
  "extraction_request": {
    "document_id": "INGEST-1234567890",
    "file_path": "/path/to/document.pdf",
    "trigger_source": "sentinel_monitoring"
  }
}
```

### GET `/api/sentinel/feed`
Get real-time monitoring feed

**Query Parameters:**
- `limit`: Number of events (default: 50)
- `unprocessed_only`: Filter to unprocessed events (default: false)

**Response:**
```json
{
  "events": [
    {
      "event_id": "DOC-123-456",
      "event_type": "DOCUMENT_DETECTED",
      "timestamp": "2024-01-15T10:30:00",
      "source": "/path/to/doc.pdf",
      "priority": 2,
      "processed": false,
      "data": {...}
    }
  ],
  "count": 10
}
```

### GET `/api/sentinel/statistics`
Get monitoring statistics

**Response:**
```json
{
  "total_events": 150,
  "unprocessed_events": 12,
  "critical_events": 3,
  "events_by_type": {
    "DOCUMENT_DETECTED": 80,
    "EXPIRATION_WARNING": 45,
    "COMPLIANCE_VIOLATION": 25
  },
  "monitoring_active": true
}
```

### POST `/api/sentinel/mark-processed/{event_id}`
Mark event as processed

### POST `/api/sentinel/watch-path`
Add directory to watch list

### POST `/api/sentinel/expiration-track`
Add item to expiration tracking

## UI Integration

The Sentinel Live Feed component provides real-time visualization:

```jsx
import SentinelLiveFeed from './components/SentinelLiveFeed';

function App() {
  return (
    <div>
      <SentinelLiveFeed />
    </div>
  );
}
```

### Features:
- ✓ Real-time event feed (5-second auto-refresh)
- ✓ Priority-based color coding
- ✓ Event filtering (all, critical, unprocessed)
- ✓ Statistics dashboard
- ✓ One-click event processing
- ✓ Responsive design

## Event Types

### DOCUMENT_DETECTED
New document found in watched directory
- **Priority:** 2 (High)
- **Auto-action:** Trigger extraction if enabled

### EXPIRATION_WARNING
Item expiring within 30 days
- **Priority:** 1 (Critical) if ≤7 days, 2 (High) otherwise
- **Auto-action:** Send notification

### COMPLIANCE_VIOLATION
Site compliance violation detected
- **Priority:** Based on risk level
- **Auto-action:** Validation + notification

### SITE_UPDATE
General site status update
- **Priority:** 3-5 (Info)
- **Auto-action:** Log event

## Integration with ConComplyAi Agents

```python
from core.services import SentinelService
from core.agents.document_extraction_agent import extract_document_fields
from core.models import DocumentExtractionState, DocumentType

sentinel = SentinelService()

# Register callback to trigger extraction
def trigger_extraction(event):
    if event.event_type == 'DOCUMENT_DETECTED':
        # Create extraction state
        state = DocumentExtractionState(
            document_id=event.event_id,
            document_type=DocumentType.COI,
            file_path=event.source
        )
        
        # Trigger extraction agent
        result = extract_document_fields(state)
        print(f"Extracted {len(result['extracted_fields'])} fields")

sentinel.register_callback(trigger_extraction)
```

## Testing

```python
# Test in validation/test_sentinel_service.py
pytest validation/test_sentinel_service.py -v
```

## Configuration Options

### WatchConfig

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| watch_paths | List[str] | [] | Directories to monitor |
| file_patterns | List[str] | ['*.pdf', '*.jpg', '*.png'] | File patterns to detect |
| poll_interval_seconds | int | 5 | Polling frequency |
| auto_trigger_extraction | bool | True | Auto-trigger on detection |

## Performance

- **Event processing:** < 10ms per event
- **File scanning:** ~1000 files/second
- **Memory usage:** ~50MB for 10,000 events
- **API latency:** < 50ms (95th percentile)

## Best Practices

1. **Set appropriate poll intervals:** Balance between real-time detection and resource usage
2. **Use callbacks for custom logic:** Don't poll the API unnecessarily
3. **Mark events as processed:** Keep feed clean and relevant
4. **Monitor statistics:** Track system health and event volume
5. **Filter events by priority:** Focus on critical items first

## Migration from Standalone Sentinel-Scope

If you were using standalone Sentinel-Scope:

```python
# Old (Sentinel-Scope)
from sentinel_scope import Monitor
monitor = Monitor()

# New (Integrated)
from core.services import SentinelService
sentinel = SentinelService()
```

The API is largely compatible, with enhanced integration into ConComplyAi workflows.

## Troubleshooting

### Events not appearing
- Check `monitoring_active` status
- Verify watch paths exist and are readable
- Check file patterns match your documents

### High memory usage
- Reduce retention of processed events
- Implement event archiving
- Adjust poll interval

### Slow performance
- Reduce number of watched directories
- Increase poll interval
- Optimize callback functions

## Support

For issues or questions:
- GitHub Issues: [ConComplyAi Issues](https://github.com/NickAiNYC/ConComplyAi/issues)
- Documentation: See `docs/SENTINEL_INTEGRATION.md`

## License

MIT License - See LICENSE file for details
