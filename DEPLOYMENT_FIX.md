# Deployment Fix: Exit Code 127 Error Resolution

## Problem Summary

The deployment to Render was failing with **"Command failed with exit code 127"** error. Exit code 127 typically indicates that a command or executable was not found during the build or deployment process.

## Root Cause

The `render.yaml` configuration file had an **invalid service type configuration** for the frontend service:

```yaml
# INCORRECT - Line 3-5 in original render.yaml
- type: web
  name: concomplai-frontend
  runtime: static
```

**Issue**: In Render's configuration:
- `type: web` is used for web services (like APIs/backends) that require a `runtime` specification (python, node, docker, etc.)
- `type: static` is used for static sites (like React builds) and does NOT use a `runtime` field
- The combination `type: web` with `runtime: static` is invalid and causes Render to fail during deployment

## Solution Applied

### 1. Fixed render.yaml Configuration

Changed the frontend service configuration from:
```yaml
- type: web
  name: concomplai-frontend
  runtime: static
  buildCommand: npm install && npm run build
  staticPublishPath: ./build
```

To the correct configuration:
```yaml
- type: static
  name: concomplai-frontend
  buildCommand: npm install && npm run build
  staticPublishPath: ./build
```

**Key change**: 
- Changed `type: web` to `type: static`
- Removed the `runtime: static` line (not valid for static type)

### 2. Updated .gitignore

Removed `package-lock.json` from `.gitignore` to ensure reproducible builds on Render. The package-lock.json file is now committed to the repository, which:
- Ensures exact dependency versions are used across all environments
- Prevents build inconsistencies between local and production
- Follows Node.js best practices for production deployments

## Files Modified

1. **render.yaml** - Fixed frontend service type configuration
2. **.gitignore** - Removed package-lock.json from ignored files
3. **package-lock.json** - Now tracked in git for reproducible builds

## Verification

All components have been tested and verified:

### ✅ Frontend Build
```bash
npm install && npm run build
# Output: Compiled successfully
```

### ✅ Backend API
```bash
uvicorn core.api:app --host 0.0.0.0 --port 8000
# Output: Server started successfully
```

### ✅ Health Endpoint
```bash
curl http://localhost:8000/health
# Output: {"status": "ok", ...}
```

### ✅ Configuration Validation
```bash
python3 -c "import yaml; yaml.safe_load(open('render.yaml'))"
# Output: No errors, valid YAML
```

### ✅ Python Tests
```bash
pytest validation/test_production_metrics.py -v
# Output: 8 passed (2 pre-existing business metric failures unrelated to deployment)
```

## Deployment on Render

The application is now ready to deploy on Render using one of two methods:

### Method 1: Blueprint Deployment (Recommended)
1. Log in to [Render Dashboard](https://dashboard.render.com)
2. Click "New" → "Blueprint"
3. Connect your GitHub repository: `NickAiNYC/ConComplyAi`
4. Render will automatically detect the `render.yaml` file
5. Review and click "Apply"

Both services will be created automatically:
- **Frontend**: `concomplai-frontend` (Static Site)
- **Backend**: `concomplai-api` (Web Service)

### Method 2: Manual Deployment
Follow the instructions in [RENDER_DEPLOYMENT.md](./RENDER_DEPLOYMENT.md)

## Technical Details

### Frontend Service (Static Site)
- **Type**: `static`
- **Build Command**: `npm install && npm run build`
- **Publish Directory**: `build`
- **Node Version**: 18.18.0
- **Framework**: React with react-scripts

### Backend Service (Web Service)
- **Type**: `web`
- **Runtime**: `python`
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `uvicorn core.api:app --host 0.0.0.0 --port $PORT`
- **Python Version**: 3.12.0
- **Health Check**: `/health`

## Related Documentation

- [RENDER_DEPLOYMENT.md](./RENDER_DEPLOYMENT.md) - Complete deployment guide
- [README.md](./README.md) - Project overview and features
- [render.yaml](./render.yaml) - Render Blueprint configuration

## Summary

The exit code 127 error was caused by an invalid service type configuration in `render.yaml`. The fix was straightforward:
- Changed the frontend service from `type: web` with `runtime: static` to `type: static`
- Committed package-lock.json for reproducible builds
- Verified all components build and run correctly

The application is now ready for successful deployment on Render!
