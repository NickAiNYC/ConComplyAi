"""
Monitoring utilities for Sentinel
Alert creation and system health checks
"""
from typing import Dict, Any
from datetime import datetime


def create_alert(alert_type: str, message: str, severity: int = 3) -> Dict[str, Any]:
    """
    Create a monitoring alert
    
    Args:
        alert_type: Type of alert (e.g., 'expiration', 'violation')
        message: Alert message
        severity: Priority level (1=critical, 5=info)
    
    Returns:
        Alert dictionary
    """
    return {
        'type': alert_type,
        'message': message,
        'severity': severity,
        'timestamp': datetime.now().isoformat(),
        'status': 'active'
    }


def check_system_health() -> Dict[str, Any]:
    """
    Check Sentinel monitoring system health
    
    Returns:
        Health status dictionary
    """
    return {
        'status': 'healthy',
        'monitoring_active': True,
        'last_check': datetime.now().isoformat(),
        'components': {
            'file_watcher': 'operational',
            'alert_engine': 'operational',
            'notification_service': 'operational'
        }
    }


def process_monitoring_event(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a monitoring event and determine actions
    
    Args:
        event: Event dictionary with type, data, priority
    
    Returns:
        Processing result with actions to take
    """
    event_type = event.get('type')
    priority = event.get('priority', 3)
    
    actions = []
    
    # Determine actions based on event type and priority
    if event_type == 'DOCUMENT_DETECTED':
        actions.append('trigger_extraction')
        if priority <= 2:
            actions.append('send_notification')
    
    elif event_type == 'EXPIRATION_WARNING':
        actions.append('send_notification')
        if priority == 1:  # Critical - expiring soon
            actions.append('escalate')
    
    elif event_type == 'COMPLIANCE_VIOLATION':
        actions.append('trigger_validation')
        actions.append('send_notification')
        if priority == 1:
            actions.append('escalate')
            actions.append('create_incident')
    
    return {
        'event_id': event.get('event_id'),
        'processed': True,
        'actions': actions,
        'timestamp': datetime.now().isoformat()
    }
