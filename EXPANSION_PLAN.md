# ConComplyAi Multi-Agent Platform - Expansion Plan

## Current State ✅
We have successfully implemented the **Guard Agent** foundation with:
- Cost tracking decorator (`@track_agent_cost`)
- DecisionProof engine (SHA-256 cryptographic audits)
- COI validation (OCR → Validation → Proof)
- Investor demo (3 test scenarios)
- Comprehensive test suite (20/20 passing)
- Documentation and benchmarks

**Cost Target Achieved**: $0.000692/doc (91% under $0.007 budget)

## Expansion Goal 🎯
Transform into a **unified multi-agent platform** with Scout, Guard, Watchman, and Fixer agents working together through cryptographic handshakes.

## Architecture Overview

```
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│  Scout   │────▶│  Guard   │────▶│  Fixer   │────▶│ Watchman │
│ (Discover)│    │(Validate)│    │(Remediate)│    │ (Monitor)│
└──────────┘     └──────────┘     └──────────┘     └──────────┘
     │                │                 │                │
     └────────────────┴─────────────────┴────────────────┘
                    AgentHandshake Chain
                  (SHA-256 linked proofs)
```

## Phase 1: Core Infrastructure Enhancement ✅ STARTED

### 1.1 AgentHandshake Protocol ✅ COMPLETE
- [x] Create `packages/core/agent_protocol.py`
- [x] Define `AgentHandshakeV2` model
- [x] Define `AgentOutputProtocol` base class
- [x] Define `AuditChain` for complete audit trails
- [x] Create helper functions for Guard integration

### 1.2 Update Existing Guard Agent (In Progress)
- [ ] Update `packages/agents/guard/validator.py` to use `AgentHandshakeV2`
- [ ] Modify `ComplianceResult` to inherit from `AgentOutputProtocol`
- [ ] Add `create_guard_handshake()` integration
- [ ] Update tests to verify handshake generation

### 1.3 Enhanced Telemetry
- [ ] Update `@track_agent_cost` to accept `AgentRole` enum
- [ ] Add agent_role column to CSV
- [ ] Track handshake_id for audit chain linking

## Phase 2: Scout Agent Implementation

### 2.1 Opportunity Discovery
**File**: `packages/agents/scout/opportunity_finder.py`

**Capabilities**:
- Scrape NYC agency portals (SCA, DDC, HPD)
- Filter for construction opportunities (>$500K)
- Calculate feasibility score based on compliance status
- Generate handshake to Guard agent

**Test Cases**:
```python
def test_scout_finds_opportunities():
    opportunities = await scout.find_opportunities(agency="SCA", max_results=5)
    assert len(opportunities) > 0
    assert opportunities[0].handshake.source_agent == AgentRole.SCOUT
    assert opportunities[0].handshake.target_agent == AgentRole.GUARD
```

**Cost Target**: < $0.05 per 100 opportunities scanned

### 2.2 Integration with Guard
- Scout generates `project_id`
- Passes opportunity metadata to Guard via handshake
- Guard validates compliance for that specific project

## Phase 3: Fixer Agent Implementation

### 3.1 Autonomous Remediation
**File**: `packages/agents/fixer/broker_liaison.py`

**Capabilities**:
- Receive deficiency from Guard agent
- Draft professional email to broker
- Include regulatory citation
- Generate secure upload portal link
- Validate email tone (Hemingway < 10)

**Test Cases**:
```python
def test_fixer_drafts_email():
    deficiency = "Missing Waiver of Subrogation"
    email = await fixer.draft_remediation_email(
        deficiency=deficiency,
        parent_handshake=guard_result.handshake
    )
    assert email.handshake.source_agent == AgentRole.FIXER
    assert email.readability_score < 10
    assert "Waiver of Subrogation" in email.email_body
```

**Cost Target**: < $0.02 per email draft

### 3.2 Email Tone Validation
- Use existing `scripts/validate_email_tone.py`
- Ensure NYC construction culture appropriateness
- No corporate jargon, direct and firm tone

## Phase 4: Watchman Agent Implementation

### 4.1 Site Monitoring
**File**: `packages/agents/watchman/site_safety_auditor.py`

**Capabilities**:
- Analyze site camera feeds (YOLOv8 for PPE detection)
- Verify worker credentials
- Check OSHA compliance (fall protection, etc.)
- Generate safety assessments with evidence

**Test Cases**:
```python
def test_watchman_analyzes_frame():
    frame = cv2.imread("sample_data/site_photos/test_frame.jpg")
    assessment = await watchman.analyze_site_camera_feed(
        camera_id="SITE_01_CAM_A",
        frame=frame,
        parent_handshake=guard_result.handshake
    )
    assert assessment.handshake.source_agent == AgentRole.WATCHMAN
    assert assessment.risk_level in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
```

**Cost Target**: < $0.15/hour of monitoring

### 4.2 Chain-of-Thought Protocol
- PPE Detection → Spatial Risk Analysis → Credential Verification
- Self-correction checklist before reporting violations
- Hallucination prevention (require bounding boxes)

## Phase 5: Master Orchestrator

### 5.1 Full Pipeline Integration
**File**: `packages/core/orchestration.py`

**Function**: `run_full_compliance_cycle()`

**Flow**:
```python
1. Scout finds opportunities
2. For each opportunity:
   a. Guard validates compliance
   b. If deficiency → Fixer remediates
   c. If approved → Watchman monitors
3. Return complete AuditChain
```

**Output**:
```json
{
  "project_id": "DDC_2026_0147",
  "audit_chain": [
    {"agent": "Scout", "hash": "a3f7...", "timestamp": "2026-02-06T10:00:00Z"},
    {"agent": "Guard", "hash": "e4d9...", "parent": "a3f7..."},
    {"agent": "Fixer", "hash": "b2c1...", "parent": "e4d9..."}
  ],
  "total_cost": 0.027,
  "processing_time": 18.3,
  "outcome": "BID_READY"
}
```

### 5.2 Integration Tests
**File**: `tests/integration/test_full_agent_chain.py`

- Test Scout → Guard → Fixer flow
- Test Scout → Guard → Watchman flow
- Verify audit chain integrity at each step
- Validate total cost stays within budget

## Phase 6: Enhanced Investor Demo

### 6.1 Multi-Agent Demo Script
**File**: `scripts/investor_demo_v2.py`

**Scenarios**:
1. **Happy Path**: Scout finds project → Guard approves → Watchman monitors
2. **Remediation Path**: Scout finds project → Guard rejects → Fixer drafts email
3. **Illegible Path**: Scout finds project → Guard marks illegible → Manual review

**Output Format**:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ConComplyAi Multi-Agent Platform - Investor Due Diligence
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 SCENARIO 1: End-to-End Success Path
🔍 Scout discovered: SCA School Renovation ($2.3M)
✅ Guard validated: Compliant (98% confidence)
👁️ Watchman monitoring: Site safety verified

Audit Chain: Scout[a3f7] → Guard[e4d9] → Watchman[b2c1]
Total Cost: $0.019
Processing Time: 14.2 seconds
Outcome: ✅ BID_READY

📊 SCENARIO 2: Remediation Required
🔍 Scout discovered: DDC Bridge Repair ($1.8M)
❌ Guard validated: Missing Waiver of Subrogation
🔧 Fixer drafted: Email to broker@example.com

Audit Chain: Scout[f5a8] → Guard[c3d1] → Fixer[9e2b]
Total Cost: $0.023
Processing Time: 16.7 seconds
Outcome: ⏳ PENDING_FIX

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
INVESTOR METRICS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Total Opportunities Processed: 3
Average Cost per Opportunity: $0.021
Total Platform Cost: $0.063
vs. Manual Process (3 × $75): $225.00

Cost Savings: 357x cheaper ✅
Audit Chain Integrity: 3/3 verified ✅
All Agents Functional: Scout, Guard, Fixer, Watchman ✅

🏆 ConComplyAi Platform is Production-Ready
```

## Phase 7: Repository Restructure

### 7.1 Directory Migration
Move existing code to new structure:
```
packages/
├── agents/
│   ├── scout/          # NEW
│   ├── guard/          # EXISTS (enhance)
│   ├── watchman/       # NEW
│   └── fixer/          # NEW
├── core/
│   ├── telemetry.py    # EXISTS (enhance)
│   ├── audit.py        # EXISTS
│   ├── agent_protocol.py # NEW (created)
│   └── orchestration.py  # NEW
```

### 7.2 Update Imports
- Update all `from packages.agents.guard` to use new structure
- Add `packages.agents` __init__.py with exports
- Update tests to use new import paths

## Implementation Priority

### Immediate (Next Session):
1. ✅ Create AgentHandshake protocol (DONE)
2. Update Guard agent to use new protocol
3. Add handshake generation to existing validator
4. Update tests to verify handshakes

### Short Term (This Week):
1. Implement Scout agent (opportunity finder)
2. Create integration test (Scout → Guard)
3. Update investor demo to show Scout + Guard

### Medium Term (Next Week):
1. Implement Fixer agent (broker liaison)
2. Implement Watchman agent (site monitoring)
3. Create master orchestrator
4. Full integration tests

### Long Term (Month):
1. Intelligence layer (geospatial data)
2. Web dashboard integration
3. Production deployment configuration

## Success Criteria

### Technical
- [ ] All 4 agents (Scout, Guard, Fixer, Watchman) functional
- [ ] AgentHandshake chain verification works
- [ ] Integration tests pass (Scout → Guard → Fixer flow)
- [ ] Cost targets met for each agent
- [ ] Audit chain integrity 100%

### Business
- [ ] Investor demo shows complete platform
- [ ] ROI calculations include all agents
- [ ] Documentation explains each agent's value
- [ ] Regulatory compliance maintained (NYC LL144)

### Quality
- [ ] Test coverage ≥ 85% for all agents
- [ ] All code type-checked with mypy --strict
- [ ] Pydantic models use ConfigDict (Pydantic V2)
- [ ] CI/CD pipeline for each agent

## Risk Mitigation

### Breaking Changes
- Keep existing Guard agent API backward compatible
- Add new handshake features alongside existing code
- Gradual migration, not big-bang rewrite

### Cost Overruns
- Monitor each agent's cost independently
- Set hard limits in telemetry decorator
- Alert if any agent exceeds budget

### Integration Complexity
- Build incrementally (Scout → Guard first)
- Test each integration before moving to next
- Maintain detailed audit logs for debugging

## Next Steps

1. **Immediate**: Update Guard agent to generate AgentHandshakeV2
2. **Next**: Implement Scout agent basics
3. **Then**: Create Scout → Guard integration test
4. **Finally**: Expand to Fixer and Watchman

This plan transforms ConComplyAi from a single Guard agent into a complete multi-agent compliance platform while maintaining the solid foundation we've built.
