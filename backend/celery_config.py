"""
Celery configuration for ConComplyAI - Using Redis for Render compatibility
"""
import os
from kombu import Exchange, Queue

# Redis configuration (Render-compatible)
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

# Celery configuration
broker_url = REDIS_URL
result_backend = REDIS_URL

# Task serialization
task_serializer = 'json'
result_serializer = 'json'
accept_content = ['json']
timezone = 'UTC'
enable_utc = True

# Task routing
task_default_queue = 'default'
task_queues = (
    Queue('default', Exchange('default'), routing_key='default'),
    Queue('violations', Exchange('violations'), routing_key='violations'),
    Queue('reports', Exchange('reports'), routing_key='reports'),
    Queue('webhooks', Exchange('webhooks'), routing_key='webhooks'),
)

# Task result settings
result_expires = 3600  # 1 hour
task_track_started = True
task_ignore_result = False

# Worker settings
worker_prefetch_multiplier = 1
worker_max_tasks_per_child = 1000
worker_disable_rate_limits = False

# Retry settings
task_acks_late = True
task_reject_on_worker_lost = True

# Monitoring
worker_send_task_events = True
task_send_sent_event = True
