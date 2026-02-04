# Render Deployment Guide for ConComplyAI

This document provides instructions for deploying the ConComplyAI application on Render.

## Overview

The application consists of two services:
1. **Frontend**: React static site (Succession Shield Enterprise Dashboard)
2. **Backend**: Python FastAPI application

## Deployment Options

### Option 1: Using Render Blueprint (Recommended)

The repository includes a `render.yaml` file that configures both services automatically.

1. Log in to [Render Dashboard](https://dashboard.render.com)
2. Click "New" → "Blueprint"
3. Connect your GitHub repository: `NickAiNYC/ConComplyAi`
4. Render will automatically detect the `render.yaml` file
5. Review the configuration and click "Apply"

Both services will be created and deployed automatically:
- `concomplai-frontend` - Static site at `https://concomplai-frontend.onrender.com`
- `concomplai-api` - Web service at `https://concomplai-api.onrender.com`

### Option 2: Manual Service Creation

#### Frontend (Static Site)

1. Click "New" → "Static Site"
2. Connect repository: `NickAiNYC/ConComplyAi`
3. Configure:
   - **Name**: `concomplai-frontend`
   - **Branch**: `main` (or your preferred branch)
   - **Build Command**: `npm install && npm run build`
   - **Publish Directory**: `build`
4. Add environment variable:
   - `NODE_VERSION`: `18.18.0`
5. Click "Create Static Site"

#### Backend (Web Service)

1. Click "New" → "Web Service"
2. Connect repository: `NickAiNYC/ConComplyAi`
3. Configure:
   - **Name**: `concomplai-api`
   - **Branch**: `main` (or your preferred branch)
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn core.api:app --host 0.0.0.0 --port $PORT`
4. Add environment variables:
   - `PYTHON_VERSION`: `3.12.0`
   - `PYTHONUNBUFFERED`: `1`
   - (Optional) Mock configuration if needed:
     - `MOCK_FAILURE_RATE`: `0.23`
     - `MOCK_LATENCY_MIN`: `0.05`
     - `MOCK_LATENCY_MAX`: `0.2`
5. Configure health check:
   - **Path**: `/health`
6. Click "Create Web Service"

## Environment Variables

### Frontend
- `NODE_VERSION`: `18.18.0` (specified in `.node-version`)

### Backend (Required)
- `PYTHON_VERSION`: `3.12.0` (specified in `.python-version`)
- `PYTHONUNBUFFERED`: `1` (for proper logging)

### Backend (Optional - Testing/Demo)
These can be configured through Render's environment variable UI:
- `MOCK_FAILURE_RATE`: Rate of mock API failures (default: 0.23)
- `MOCK_LATENCY_MIN`: Minimum mock API latency in seconds (default: 0.05)
- `MOCK_LATENCY_MAX`: Maximum mock API latency in seconds (default: 0.2)

## Health Checks

The backend API includes a health check endpoint:
- **URL**: `/health`
- **Method**: GET
- **Response**: JSON with system status

Example response:
```json
{
  "status": "ok",
  "version": "1.0.0",
  "timestamp": "2026-02-04T07:55:37.342996",
  "components": {
    "supervisor": "healthy",
    "vision_model": "mock_ready",
    "redis": "connected",
    "model_registry": "available"
  },
  "config": {
    "accuracy_target": 0.87,
    "cost_per_site_budget": 0.04,
    "processing_sla_seconds": 7200
  }
}
```

## Monitoring

The backend also includes a Prometheus-compatible metrics endpoint:
- **URL**: `/metrics`
- **Method**: GET

## Files Added for Deployment

- `render.yaml` - Render Blueprint configuration
- `.node-version` - Node.js version specification
- `.python-version` - Python version specification
- `Procfile` - Alternative deployment configuration
- `package.json` - Updated with engine requirements

## Troubleshooting

### Frontend Build Fails
- Ensure Node.js version is 18.18.0 or higher
- Check that all dependencies are properly installed
- Verify the build command: `npm install && npm run build`

### Backend Fails to Start
- Ensure Python version is 3.12.0
- Check that all requirements are installed
- Verify the start command includes the PORT variable
- Check health endpoint: `curl https://your-service.onrender.com/health`

### Application Not Responding
- Check Render logs for errors
- Verify environment variables are set correctly
- Ensure the health check path is `/health`

## Support

For issues specific to Render deployment:
- [Render Documentation](https://render.com/docs)
- [Render Community Forum](https://community.render.com)

For application-specific issues:
- Check the repository README.md
- Review application logs in Render dashboard
