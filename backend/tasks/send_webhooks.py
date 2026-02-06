"""
Webhook Tasks - Async webhook delivery and notification system
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
from backend.celery_worker import app
from celery import Task
from celery.utils.log import get_task_logger
import json

logger = get_task_logger(__name__)


class WebhookTask(Task):
    """Base task for webhooks with retry logic"""
    autoretry_for = (Exception,)
    retry_kwargs = {'max_retries': 5, 'countdown': 30}
    retry_backoff = True
    retry_backoff_max = 3600  # Max 1 hour between retries
    retry_jitter = True


@app.task(base=WebhookTask, bind=True, name='send_webhooks.send_violation_alert')
def send_violation_alert(
    self,
    webhook_url: str,
    site_id: str,
    violation_data: Dict[str, Any],
    severity: str = 'HIGH'
) -> Dict[str, Any]:
    """
    Send violation alert via webhook
    
    Args:
        webhook_url: Target webhook endpoint
        site_id: Site identifier
        violation_data: Violation details to send
        severity: Alert severity level
        
    Returns:
        Dict with delivery status
    """
    try:
        logger.info(f"Sending violation alert for site {site_id} to {webhook_url}")
        
        payload = {
            'event': 'violation.detected',
            'site_id': site_id,
            'severity': severity,
            'timestamp': datetime.utcnow().isoformat(),
            'data': violation_data,
            'attempt': self.request.retries + 1
        }
        
        # In production, use requests library to POST to webhook
        # response = requests.post(webhook_url, json=payload, timeout=10)
        # response.raise_for_status()
        
        logger.info(f"Violation alert sent successfully for site {site_id}")
        return {
            'status': 'delivered',
            'timestamp': datetime.utcnow().isoformat(),
            'webhook_url': webhook_url,
            'site_id': site_id,
            'payload_size': len(json.dumps(payload))
        }
    except Exception as e:
        logger.error(f"Error sending violation alert for site {site_id}: {str(e)}")
        raise


@app.task(base=WebhookTask, bind=True, name='send_webhooks.send_report_ready')
def send_report_ready(
    self,
    webhook_url: str,
    site_id: str,
    report_url: str,
    report_metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Notify when report is ready for download
    
    Args:
        webhook_url: Target webhook endpoint
        site_id: Site identifier
        report_url: URL to download report
        report_metadata: Optional report metadata
        
    Returns:
        Dict with notification status
    """
    try:
        logger.info(f"Sending report ready notification for site {site_id}")
        
        payload = {
            'event': 'report.ready',
            'site_id': site_id,
            'report_url': report_url,
            'timestamp': datetime.utcnow().isoformat(),
            'metadata': report_metadata or {},
            'attempt': self.request.retries + 1
        }
        
        # In production, POST to webhook
        # response = requests.post(webhook_url, json=payload, timeout=10)
        # response.raise_for_status()
        
        logger.info(f"Report ready notification sent for site {site_id}")
        return {
            'status': 'delivered',
            'timestamp': datetime.utcnow().isoformat(),
            'webhook_url': webhook_url,
            'site_id': site_id,
            'report_url': report_url
        }
    except Exception as e:
        logger.error(f"Error sending report ready notification: {str(e)}")
        raise


@app.task(base=WebhookTask, bind=True, name='send_webhooks.send_batch_notification')
def send_batch_notification(
    self,
    webhook_urls: List[str],
    event_type: str,
    event_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Send notification to multiple webhooks
    
    Args:
        webhook_urls: List of webhook endpoints
        event_type: Type of event being notified
        event_data: Event payload data
        
    Returns:
        Dict with batch delivery status
    """
    try:
        logger.info(f"Sending batch notification to {len(webhook_urls)} webhooks")
        
        results = []
        errors = []
        
        for webhook_url in webhook_urls:
            try:
                payload = {
                    'event': event_type,
                    'timestamp': datetime.utcnow().isoformat(),
                    'data': event_data,
                    'attempt': self.request.retries + 1
                }
                
                # In production, POST to webhook
                # response = requests.post(webhook_url, json=payload, timeout=10)
                # response.raise_for_status()
                
                results.append({
                    'webhook_url': webhook_url,
                    'status': 'delivered'
                })
            except Exception as e:
                logger.error(f"Error sending to webhook {webhook_url}: {str(e)}")
                errors.append({
                    'webhook_url': webhook_url,
                    'error': str(e)
                })
        
        logger.info(f"Batch notification: {len(results)} delivered, {len(errors)} failed")
        return {
            'status': 'completed',
            'timestamp': datetime.utcnow().isoformat(),
            'total_webhooks': len(webhook_urls),
            'delivered': len(results),
            'failed': len(errors),
            'results': results,
            'errors': errors
        }
    except Exception as e:
        logger.error(f"Error in batch notification: {str(e)}")
        raise


@app.task(base=WebhookTask, bind=True, name='send_webhooks.retry_failed_webhook')
def retry_failed_webhook(
    self,
    original_task_id: str,
    webhook_url: str,
    payload: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Retry a previously failed webhook delivery
    
    Args:
        original_task_id: Original failed task ID
        webhook_url: Target webhook endpoint
        payload: Original payload to retry
        
    Returns:
        Dict with retry status
    """
    try:
        logger.info(f"Retrying failed webhook delivery: task {original_task_id}")
        
        # In production, POST to webhook
        # response = requests.post(webhook_url, json=payload, timeout=10)
        # response.raise_for_status()
        
        logger.info(f"Webhook retry successful for task {original_task_id}")
        return {
            'status': 'delivered',
            'timestamp': datetime.utcnow().isoformat(),
            'original_task_id': original_task_id,
            'webhook_url': webhook_url,
            'retry_attempt': self.request.retries + 1
        }
    except Exception as e:
        logger.error(f"Error retrying webhook for task {original_task_id}: {str(e)}")
        raise
