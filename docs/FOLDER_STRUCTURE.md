# Recommended Folder Structure for ConComplyAi
## Modular Monorepo Architecture

This document outlines the recommended folder structure for maintaining modularity across agents, Pydantic models, and React components in the ConComplyAi Self-Healing Compliance Suite.

## Overview

The architecture follows a **monorepo pattern** with clear separation of concerns:

- **`/packages`**: Shared code between backend and frontend
- **`/core`**: Backend Python agents and services
- **`/src`**: React frontend components
- **`/validation`**: Test suites
- **`/docs`**: Documentation

---

## Complete Folder Structure

```
ConComplyAi/
├── packages/                          # 📦 Shared monorepo packages
│   ├── shared/                        # Shared models & utilities
│   │   ├── models/                    # ⭐ 9 Core Pydantic Models
│   │   │   ├── __init__.py           # Exports all models
│   │   │   ├── document_models.py    # Document extraction, fields, PII
│   │   │   ├── insurance_models.py   # COI, Insurance Coverage
│   │   │   ├── compliance_models.py  # OSHA, Licenses, Lien Waivers
│   │   │   └── audit_models.py       # Audit trail (2026 standards)
│   │   ├── utils/                     # Shared utilities
│   │   │   ├── validators.py         # Custom validators
│   │   │   ├── formatters.py         # Date/currency formatting
│   │   │   └── constants.py          # Shared constants
│   │   └── types/                     # TypeScript type generation
│   │       └── generated.ts          # Auto-generated from Pydantic
│   │
│   └── sentinel/                      # Sentinel monitoring module
│       ├── __init__.py               # Sentinel exports
│       ├── README.md                 # Sentinel documentation
│       └── src/
│           ├── __init__.py
│           └── monitoring.py         # Alert & health check utils
│
├── core/                             # 🐍 Backend Python application
│   ├── __init__.py
│   ├── api.py                        # ⭐ FastAPI endpoints
│   ├── config.py                     # Configuration
│   ├── model_registry.py             # A/B testing
│   ├── models.py                     # Legacy models (migrate to /packages/shared)
│   │
│   ├── agents/                       # 🤖 AI Agents (11 total)
│   │   ├── __init__.py
│   │   │
│   │   # Multi-Agent Collaboration
│   │   ├── vision_agent.py          # OSHA-focused visual analysis
│   │   ├── permit_agent.py          # NYC Building Code specialist
│   │   ├── synthesis_agent.py       # Cross-validation & consensus
│   │   ├── red_team_agent.py        # Adversarial validation
│   │   ├── risk_scorer.py           # Final risk assessment
│   │   │
│   │   # Document Processing
│   │   ├── document_extraction_agent.py     # OCR & field extraction
│   │   ├── insurance_validation_agent.py    # COI validation
│   │   ├── document_quality_agent.py        # Quality assessment
│   │   │
│   │   # Original Agents
│   │   ├── violation_detector.py    # Original detector
│   │   ├── report_generator.py      # Report generation
│   │   │
│   │   # ⭐ NEW: Self-Healing Suite
│   │   └── outreach_agent.py        # Autonomous correction requests
│   │
│   ├── services/                    # 🛠️ Backend Services
│   │   ├── __init__.py
│   │   ├── sentinel_service.py      # ⭐ File watching, monitoring
│   │   ├── sentinel_heartbeat.py    # ⭐ High-risk escalation
│   │   └── audit_logger.py          # ⭐ Immutable audit trail
│   │
│   ├── supervisor.py                # LangGraph orchestration
│   ├── multi_agent_supervisor.py   # Multi-agent parallel execution
│   └── synthetic_generator.py      # Synthetic data pipeline
│
├── src/                             # ⚛️ React Frontend
│   ├── index.js                    # Entry point
│   ├── index.css                   # Global styles
│   ├── App.js                      # ⭐ Main app with navigation
│   │
│   └── components/                 # React Components
│       ├── SuccessionShieldEnterprise.jsx    # Site compliance dashboard
│       ├── SentinelLiveFeed.jsx              # ⭐ Real-time monitoring
│       ├── DocumentUploadStation.jsx         # Document upload interface
│       ├── ContractorDocVerifier.jsx         # Comparison view
│       │
│       # Future components
│       ├── AuditTrailViewer.jsx              # Human review interface
│       ├── HeartbeatDashboard.jsx            # Contractor risk status
│       └── OutreachManager.jsx               # Outreach history
│
├── validation/                      # 🧪 Test Suites
│   ├── test_production_metrics.py  # Original tests (10 tests)
│   ├── test_multi_agent.py         # Multi-agent tests (9 tests)
│   ├── test_synthetic_data.py      # Synthetic data tests (10 tests)
│   ├── test_document_processing.py # Document tests (21 tests)
│   ├── test_sentinel_service.py    # ⭐ Sentinel tests (22 tests)
│   │
│   # Future test files
│   ├── test_outreach_agent.py      # Outreach agent tests
│   ├── test_sentinel_heartbeat.py  # Heartbeat integration tests
│   ├── test_audit_logger.py        # Audit trail tests
│   │
│   ├── load_test.py                # Load testing
│   ├── chaos_test.py               # Chaos engineering
│   └── metrics_dashboard.py        # Streamlit observability
│
├── docs/                           # 📚 Documentation
│   ├── PROJECT_JOURNEY.md
│   ├── INTERVIEW_TALKING_POINTS.md
│   ├── MULTI_AGENT_EXAMPLES.md
│   ├── SYNTHETIC_DATA_PIPELINE.md
│   ├── DOCUMENT_PROCESSING.md
│   ├── ARCHITECTURE_DECISIONS.md
│   ├── SCALING_TO_1000_SITES.md
│   │
│   # ⭐ NEW Documentation
│   ├── SELF_HEALING_ARCHITECTURE.md    # Self-healing features
│   ├── AUDIT_TRAIL_GUIDE.md            # Human-on-the-loop
│   └── FOLDER_STRUCTURE.md             # This file
│
├── backend/                        # Celery workers (optional)
│   ├── __init__.py
│   ├── celery_config.py
│   ├── celery_worker.py
│   └── tasks/
│
├── infra/                          # Infrastructure configs
│   ├── docker-compose.yml
│   ├── kubernetes/
│   └── terraform/
│
├── public/                         # Static assets
│   └── index.html
│
├── .github/                        # CI/CD workflows
│   └── workflows/
│       ├── ci.yml
│       └── deploy.yml
│
├── requirements.txt                # Python dependencies
├── package.json                    # Node dependencies
├── setup.py                        # Python package setup
├── README.md                       # Main documentation
└── .gitignore

```

---

## Key Design Principles

### 1. **Separation of Concerns**

Each layer has a clear responsibility:
- **`/packages/shared`**: Models and types (no business logic)
- **`/core/agents`**: AI agents (autonomous decision makers)
- **`/core/services`**: Infrastructure services (monitoring, logging)
- **`/src/components`**: UI components (presentation only)

### 2. **Dependency Flow**

```
Frontend (React)
      ↓
   API Layer
      ↓
  Services Layer
      ↓
   Agents Layer
      ↓
Shared Models (packages/shared)
```

**Rule**: Lower layers never import from upper layers.

### 3. **Import Patterns**

#### ✅ Correct Imports

```python
# Agent importing shared models
from packages.shared.models import COIDocument, ExpirationStatus

# Service importing agents
from core.agents.outreach_agent import OutreachAgent

# API importing services
from core.services import SentinelService
```

#### ❌ Incorrect Imports

```python
# NEVER: Shared models importing agents
from core.agents import VisionAgent  # ❌

# NEVER: Agent importing from API
from core.api import app  # ❌
```

### 4. **Modular Agent Pattern**

Each agent is self-contained:
- Single file per agent
- Clear input/output contracts (Pydantic models)
- No cross-agent imports (use supervisor for orchestration)
- Audit logging built-in

```python
# Template for new agent
from packages.shared.models import DocumentExtractionState
from core.services.audit_logger import log_autonomous_action

class MyNewAgent:
    def process(self, state: DocumentExtractionState):
        # ... agent logic ...
        
        # Log decision
        log_autonomous_action(
            action=AuditAction.AUTONOMOUS_DECISION,
            agent_name="my_new_agent",
            decision_data={...},
            reasoning="...",
            action_taken="..."
        )
        
        return result
```

### 5. **Modular Component Pattern**

React components follow atomic design:
- One component per file
- Props clearly typed (use JSDoc or TypeScript)
- Minimal state management
- API calls in parent components

```jsx
/**
 * ComponentName.jsx
 * @param {Object} props
 * @param {string} props.data - Description
 */
const ComponentName = ({ data }) => {
  // Component logic
  return <div>{data}</div>
}
```

---

## Migration Guide

### Moving from Legacy Structure

#### Phase 1: Models (✅ Complete)
```bash
# Models moved to /packages/shared/models/
- DocumentExtractionState
- COIDocument, OSHALog, License, LienWaiver
- InsuranceCoverage, ExtractedField
- PIIRedaction
- AuditLogEntry, DecisionLog  # NEW
```

#### Phase 2: Update Imports
```python
# Old
from core.models import COIDocument

# New
from packages.shared.models import COIDocument
```

#### Phase 3: TypeScript Generation (Future)
```bash
# Generate TypeScript types from Pydantic
python scripts/generate_types.py
# Output: packages/shared/types/generated.ts
```

---

## Testing Structure

### Test Organization

```
validation/
├── unit/                    # Unit tests for individual components
│   ├── test_agents/
│   ├── test_services/
│   └── test_models/
│
├── integration/             # Integration tests
│   ├── test_api_endpoints.py
│   ├── test_agent_workflows.py
│   └── test_sentinel_heartbeat.py
│
├── e2e/                    # End-to-end tests
│   └── test_full_workflow.py
│
└── performance/            # Performance tests
    ├── load_test.py
    └── stress_test.py
```

### Test Naming Convention

```python
# test_{component}_{feature}.py
test_outreach_agent_correction_messages.py
test_sentinel_heartbeat_risk_escalation.py
test_audit_logger_immutability.py
```

---

## Adding New Features

### New Agent

1. Create file: `core/agents/my_new_agent.py`
2. Implement agent class with clear interface
3. Add to `core/agents/__init__.py`
4. Create tests: `validation/test_my_new_agent.py`
5. Document in `docs/`

### New Service

1. Create file: `core/services/my_service.py`
2. Add to `core/services/__init__.py`
3. Integrate with API if needed
4. Create tests
5. Document

### New Model

1. Add to appropriate file in `packages/shared/models/`
2. Export from `__init__.py`
3. Update TypeScript types (future)
4. Add validation tests

### New Component

1. Create file: `src/components/MyComponent.jsx`
2. Add to navigation in `App.js`
3. Create API integration if needed
4. Add to Storybook (future)

---

## Best Practices

### 1. **Keep It Modular**
- Each file should have a single, clear purpose
- Avoid "god objects" that do everything
- Extract common logic to utilities

### 2. **Document As You Go**
- Every new agent needs docstring
- API endpoints need OpenAPI descriptions
- Complex logic needs inline comments

### 3. **Test First, Then Implement**
- Write test for expected behavior
- Implement to make test pass
- Refactor for clarity

### 4. **Cost Awareness**
- Every agent logs cost
- Budget alerts at $0.01/doc
- Maintain $0.0066/doc efficiency target

### 5. **Audit Everything**
- All autonomous decisions logged
- Use `log_autonomous_action()` helper
- Human review for P1 decisions

---

## Performance Considerations

### File Organization Impact

**Good**: Modular structure
- Faster import times
- Easy to parallelize
- Better caching

**Bad**: Monolithic files
- Slow startup
- Hard to test
- Cache invalidation issues

### Recommended Limits

- **Agent file**: < 500 lines
- **Service file**: < 800 lines
- **Component file**: < 300 lines
- **Model file**: < 600 lines

If exceeding limits, split into sub-modules.

---

## Future Enhancements

### Planned Structure Updates

1. **TypeScript Integration**
   ```
   packages/shared/types/
   └── generated.ts  # Auto-generated from Pydantic
   ```

2. **Microservices Split**
   ```
   services/
   ├── document-processor/
   ├── risk-analyzer/
   └── notification-service/
   ```

3. **Plugin System**
   ```
   plugins/
   ├── custom-validators/
   └── industry-specific/
   ```

---

## Questions?

For questions about folder structure or adding new features:
1. Check this document
2. Review existing patterns in similar files
3. Ask in #architecture channel

**Remember**: Consistency > Perfection. Follow existing patterns.

---

**Last Updated**: 2026-02-06
**Version**: 2.0.0-self-healing
