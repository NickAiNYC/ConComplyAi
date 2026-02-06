"""
Sentinel Package - Real-time Monitoring Module
Integrated from Sentinel-Scope into ConComplyAi

This package provides real-time monitoring capabilities including:
- File system watching for new documents
- Expiration tracking (30-day warnings)
- Compliance event monitoring
- Unified ingestion triggering

Usage:
    from packages.sentinel import SentinelMonitor
    
    monitor = SentinelMonitor()
    monitor.start_watching('/path/to/documents')
"""

__version__ = '1.0.0'
__author__ = 'ConComplyAi Team'

from core.services.sentinel_service import (
    SentinelService,
    MonitoringEvent,
    MonitoringEventType,
    WatchConfig
)

# Alias for backward compatibility
SentinelMonitor = SentinelService

__all__ = [
    'SentinelService',
    'SentinelMonitor',
    'MonitoringEvent',
    'MonitoringEventType',
    'WatchConfig'
]
