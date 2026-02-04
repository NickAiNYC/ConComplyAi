#!/bin/bash
# Entrypoint script for ConComplyAI - Handles dual service startup for Render deployment
# Supports running API server, Celery worker, or both

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Log functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Service selection based on environment variable
SERVICE_TYPE="${SERVICE_TYPE:-api}"  # Default to API service

log_info "Starting ConComplyAI service: $SERVICE_TYPE"

# Validate environment
if [ -z "$PORT" ] && [ "$SERVICE_TYPE" = "api" ]; then
    log_warn "PORT not set, using default 8000"
    export PORT=8000
fi

if [ -z "$REDIS_URL" ] && [ "$SERVICE_TYPE" = "worker" ]; then
    log_warn "REDIS_URL not set, using default redis://localhost:6379/0"
    export REDIS_URL="redis://localhost:6379/0"
fi

# Start appropriate service(s)
case "$SERVICE_TYPE" in
    api)
        log_info "Starting FastAPI server on port $PORT"
        exec uvicorn core.api:app --host 0.0.0.0 --port "$PORT" --workers 2
        ;;
    
    worker)
        log_info "Starting Celery worker with Redis broker: $REDIS_URL"
        exec celery -A backend.celery_worker worker --loglevel=info --concurrency=2
        ;;
    
    both)
        log_info "Starting both API server and Celery worker"
        
        # Start API server in background
        log_info "Starting FastAPI server on port $PORT (background)"
        uvicorn core.api:app --host 0.0.0.0 --port "$PORT" --workers 1 &
        API_PID=$!
        
        # Give API time to start
        sleep 5
        
        # Start Celery worker in foreground
        log_info "Starting Celery worker (foreground)"
        celery -A backend.celery_worker worker --loglevel=info --concurrency=1 &
        WORKER_PID=$!
        
        # Trap signals and ensure both processes are killed
        trap 'log_info "Shutting down services..."; kill $API_PID $WORKER_PID 2>/dev/null; exit 0' SIGTERM SIGINT
        
        # Wait for both processes
        wait $API_PID $WORKER_PID
        ;;
    
    *)
        log_error "Unknown SERVICE_TYPE: $SERVICE_TYPE"
        log_error "Valid options: api, worker, both"
        exit 1
        ;;
esac
