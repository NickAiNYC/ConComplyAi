"""
Celery Worker for ConComplyAI - Redis-backed task processing for Render deployment
"""
import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from celery import Celery
from . import celery_config

# Initialize Celery app
app = Celery('concomplai')
app.config_from_object(celery_config)

# Auto-discover tasks from all task modules
app.autodiscover_tasks(['backend.tasks'])


@app.task(bind=True)
def debug_task(self):
    """Debug task for testing Celery configuration"""
    return f'Request: {self.request!r}'


def main():
    """Entry point for celery worker command"""
    app.start()


if __name__ == '__main__':
    main()
