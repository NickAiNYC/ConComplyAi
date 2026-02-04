"""
Violation Scanning Tasks - Async compliance checking for construction sites
"""
from typing import Dict, Any, List
from datetime import datetime
from backend.celery_worker import app
from celery import Task
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)


class ViolationScanTask(Task):
    """Base task for violation scanning with error handling"""
    autoretry_for = (Exception,)
    retry_kwargs = {'max_retries': 3, 'countdown': 5}
    retry_backoff = True
    retry_backoff_max = 600
    retry_jitter = True


@app.task(base=ViolationScanTask, bind=True, name='scan_violations.scan_site')
def scan_site(self, site_id: str, image_url: str = None) -> Dict[str, Any]:
    """
    Scan a construction site for violations
    
    Args:
        site_id: Unique identifier for the construction site
        image_url: Optional URL to site image for vision analysis
        
    Returns:
        Dict containing scan results with violations and risk assessment
    """
    try:
        logger.info(f"Starting violation scan for site: {site_id}")
        
        # Import here to avoid circular dependencies
        from core.supervisor import run_compliance_check
        
        # Run compliance check
        result = run_compliance_check(site_id)
        
        logger.info(f"Completed violation scan for site: {site_id}")
        return {
            'site_id': site_id,
            'status': 'completed',
            'timestamp': datetime.utcnow().isoformat(),
            'result': result
        }
    except Exception as e:
        logger.error(f"Error scanning site {site_id}: {str(e)}")
        raise


@app.task(base=ViolationScanTask, bind=True, name='scan_violations.batch_scan')
def batch_scan(self, site_ids: List[str]) -> Dict[str, Any]:
    """
    Scan multiple construction sites in batch
    
    Args:
        site_ids: List of site identifiers to scan
        
    Returns:
        Dict with batch scan results and summary
    """
    try:
        logger.info(f"Starting batch scan for {len(site_ids)} sites")
        
        results = []
        errors = []
        
        for site_id in site_ids:
            try:
                result = scan_site.apply_async(args=[site_id])
                results.append({'site_id': site_id, 'task_id': result.id})
            except Exception as e:
                logger.error(f"Error queuing scan for site {site_id}: {str(e)}")
                errors.append({'site_id': site_id, 'error': str(e)})
        
        logger.info(f"Batch scan queued: {len(results)} successful, {len(errors)} errors")
        return {
            'status': 'queued',
            'timestamp': datetime.utcnow().isoformat(),
            'total_sites': len(site_ids),
            'queued': len(results),
            'errors': len(errors),
            'results': results,
            'error_details': errors
        }
    except Exception as e:
        logger.error(f"Error in batch scan: {str(e)}")
        raise


@app.task(base=ViolationScanTask, bind=True, name='scan_violations.rescan_site')
def rescan_site(self, site_id: str, reason: str = None) -> Dict[str, Any]:
    """
    Re-scan a site (e.g., after remediation or dispute)
    
    Args:
        site_id: Site identifier
        reason: Optional reason for rescan
        
    Returns:
        Dict with rescan results
    """
    try:
        logger.info(f"Rescanning site {site_id}. Reason: {reason}")
        
        result = scan_site.apply_async(args=[site_id])
        
        return {
            'site_id': site_id,
            'status': 'rescan_queued',
            'reason': reason,
            'timestamp': datetime.utcnow().isoformat(),
            'task_id': result.id
        }
    except Exception as e:
        logger.error(f"Error rescanning site {site_id}: {str(e)}")
        raise
