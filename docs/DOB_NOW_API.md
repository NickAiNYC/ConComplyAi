# DOB NOW API Integration Guide

## Overview

The DOB NOW API Client provides production-grade integration with NYC Department of Buildings' permit system. This guide covers setup, usage, and best practices.

## Features

- **Circuit Breaker Pattern**: Automatic failure handling (3 failures → 30s timeout)
- **Exponential Backoff**: 2s → 4s → 10s retry delays with jitter
- **Rate Limiting**: 50 requests/minute (configurable)
- **Connection Pooling**: Supports 10,000+ concurrent sites
- **Mock Mode**: Safe testing without API calls

## Installation

```bash
pip install pybreaker requests  # Dependencies
```

## Configuration

Set environment variables:

```bash
export DOB_NOW_API_KEY="your_api_key_here"
export DOB_NOW_BASE_URL="https://data.cityofnewyork.us"
export DOB_NOW_RATE_LIMIT="50"  # requests per minute
export DOB_NOW_TIMEOUT="30"  # seconds
export DOB_NOW_USE_MOCK="false"  # Set to false for production
```

## Quick Start

### Basic Usage

```python
from packages.core.dob_now_api_client import DOBNowAPIClient

# Create client (uses environment variables)
client = DOBNowAPIClient(use_mock=False)

# Get permit status
permit = client.get_permit_status("BLD-2024-12345")
print(f"Status: {permit.status}")
print(f"Superintendent: {permit.superintendent_name}")

# Get inspections
inspections = client.get_inspections("BLD-2024-12345")
for inspection in inspections:
    print(f"{inspection.inspection_type}: {inspection.status}")

# Get violations
violations = client.get_violations("BLD-2024-12345")
for violation in violations:
    print(f"{violation.violation_type}: ${violation.fine_amount}")
```

### Health Check

```python
from packages.core.dob_now_api_client import check_api_health

if check_api_health():
    print("DOB NOW API is healthy")
else:
    print("DOB NOW API is down or degraded")
```

### Using Mock Mode (Development)

```python
# Mock mode for development/testing
client = DOBNowAPIClient(use_mock=True)

# Returns realistic test data without API calls
permit = client.get_permit_status("BLD-2024-TEST")
```

## Advanced Features

### Circuit Breaker

The client automatically manages failures:

```python
# Circuit breaker opens after 3 consecutive failures
# Prevents cascading failures
# Automatically resets after 30 seconds
try:
    permit = client.get_permit_status("BLD-2024-12345")
except ConnectionError as e:
    print(f"Circuit breaker open: {e}")
    # Wait for reset or implement fallback
```

### Metrics Tracking

```python
metrics = client.get_metrics()
print(f"Total requests: {metrics['total_requests']}")
print(f"Success rate: {metrics['success_rate']:.2%}")
print(f"Avg response time: {metrics['avg_response_time_ms']:.0f}ms")
print(f"Circuit breaker state: {metrics['circuit_breaker_state']}")
```

### Rate Limiting

```python
# Custom rate limit
client = DOBNowAPIClient(rate_limit=100)  # 100 requests/minute

# Rate limiting is automatic
# Client will sleep if limit is reached
```

## Data Models

### PermitStatus

```python
class PermitStatus:
    permit_number: str
    status: str  # ACTIVE, EXPIRED, PENDING, APPROVED, REJECTED
    filing_date: datetime
    expiration_date: Optional[datetime]
    applicant_name: str
    site_address: str
    work_type: str
    superintendent_name: Optional[str]
    superintendent_license: Optional[str]
    bbl: Optional[str]
```

### InspectionSchedule

```python
class InspectionSchedule:
    inspection_id: str
    permit_number: str
    inspection_type: str
    scheduled_date: Optional[datetime]
    inspector_name: Optional[str]
    status: str  # SCHEDULED, COMPLETED, FAILED, PENDING
    result: Optional[str]
```

### ViolationRecord

```python
class ViolationRecord:
    violation_id: str
    permit_number: str
    issued_date: datetime
    violation_type: str  # OSHA, DOB, ECB
    description: str
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW
    fine_amount: float
    status: str  # OPEN, RESOLVED, APPEALED
```

## Error Handling

### Best Practices

```python
from pybreaker import CircuitBreakerError

try:
    permit = client.get_permit_status("BLD-2024-12345")
except ConnectionError as e:
    # Network/API failure
    print(f"API unavailable: {e}")
    # Implement fallback or retry later
except CircuitBreakerError as e:
    # Circuit breaker is open
    print(f"Service temporarily unavailable: {e}")
    # Wait for circuit breaker reset
except Exception as e:
    # Other errors
    print(f"Unexpected error: {e}")
```

## Production Deployment

### Requirements

1. Valid DOB NOW API key
2. Whitelist IP addresses with NYC DOB
3. Monitor circuit breaker state
4. Set up alerts for high failure rates

### Monitoring

```python
# Regular health checks
import time

while True:
    status = client.get_health_status()
    
    if status.status != "healthy":
        # Alert operations team
        print(f"⚠️ API degraded: {status.success_rate:.0%} success rate")
    
    time.sleep(60)  # Check every minute
```

### Performance Tuning

```python
# High-volume configuration
client = DOBNowAPIClient(
    rate_limit=100,  # Increase if approved by DOB
    timeout=60,      # Longer timeout for large responses
    use_mock=False
)
```

## Integration with ConComplyAi

### With LL149 Engine

```python
from packages.core.dob_now_api_client import DOBNowAPIClient
from packages.core.nyc_2026_regulations import is_ll149_superintendent_conflict

client = DOBNowAPIClient(use_mock=False)

# Check superintendent conflicts
permit = client.get_permit_status("BLD-2024-12345")
if permit.superintendent_license:
    # Get all active permits for this superintendent
    # (would need batch endpoint in production)
    conflict = is_ll149_superintendent_conflict(
        cs_license_number=permit.superintendent_license,
        active_permits=[],  # Populate from batch query
        cs_name=permit.superintendent_name
    )
    if conflict:
        print(f"⚠️ LL149 violation detected!")
```

### With LL11 Facade Tracker

```python
from packages.core.ll11_facade_inspection_tracker import LL11FacadeInspectionTracker

tracker = LL11FacadeInspectionTracker()
permit = client.get_permit_status("BLD-2024-12345")

# Check if building requires FISP
if permit.bbl:
    # Query building info and run facade check
    # ...
```

## Troubleshooting

### Common Issues

**Issue**: `ConnectionError: DOB NOW API request failed`
- **Solution**: Check API key, network connectivity, DOB API status

**Issue**: `CircuitBreakerError: Circuit breaker is open`
- **Solution**: Wait 30 seconds for reset, or check if DOB API is down

**Issue**: Rate limit exceeded
- **Solution**: Reduce request frequency or request higher rate limit from DOB

**Issue**: Mock data returned in production
- **Solution**: Set `DOB_NOW_USE_MOCK=false` environment variable

## API Limits

- **Rate Limit**: 50 requests/minute (default)
- **Timeout**: 30 seconds per request
- **Daily Quota**: Contact DOB for limits
- **Concurrent Connections**: 10,000+ supported

## Support

- **DOB NOW Portal**: https://a810-bisweb.nyc.gov/bisweb/
- **ConComplyAi Support**: support@concomply.ai
- **Documentation**: https://docs.concomply.ai

## Changelog

### v2026.1.0 (2026-02-12)
- Initial production release
- Circuit breaker pattern
- Exponential backoff with jitter
- Rate limiting (50 req/min)
- Mock mode for development
- Comprehensive error handling

---

**VALUE PROPOSITION**: "Stop using our mocks. Go live."

Real-time DOB data = Real-time compliance = Zero surprises.
