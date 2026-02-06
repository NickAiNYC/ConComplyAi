# Scout Agent - NYC Permit Opportunity Discovery

The Scout Agent is the first agent in the ConComplyAi multi-agent pipeline. It discovers high-value construction permit opportunities from NYC DOB data and initiates the compliance validation workflow.

## Purpose

Scout monitors the NYC Department of Buildings (DOB) Permit Issuance dataset to identify new construction projects that may require compliance validation services. It implements the "Veteran Skeptic" filtering strategy to focus on high-value opportunities.

## Key Features

- **Socrata API Integration**: Queries NYC Open Data for DOB Permit Issuance records
- **Veteran Skeptic Logic**: Filters out low-value permits (< $5,000 estimated fee)
- **Job Type Filtering**: Focuses on 'NB' (New Building) and 'A1' (Major Alteration) permits
- **Time-Window Filtering**: Configurable lookback period (default: 24 hours)
- **AgentHandshakeV2 Protocol**: Creates cryptographic audit trail for handoffs
- **Cost-Efficient**: Uses minimal LLM tokens (~$0.000138/search)

## Usage

### Basic Usage

```python
from packages.agents.scout.finder import find_opportunities, create_scout_handshake
from packages.core.agent_protocol import AgentRole

# Discover opportunities
result = find_opportunities(
    hours_lookback=24,
    min_estimated_fee=5000.0,
    job_types=["NB", "A1"],
    use_mock=True  # Set False for production
)

opportunities = result["opportunities"]
decision_proof = result["decision_proof"]

# Create handshake for next agent
for opportunity in opportunities:
    handshake = create_scout_handshake(
        opportunity=opportunity,
        decision_proof_hash=decision_proof.proof_hash,
        target_agent=AgentRole.GUARD
    )
    # Pass handshake to Guard agent
```

### Scout Output Structure

```python
{
    "opportunities": List[Opportunity],
    "search_criteria": {
        "hours_lookback": 24,
        "min_estimated_fee": 5000.0,
        "job_types": ["NB", "A1"]
    },
    "total_permits_scanned": 10,
    "opportunities_found": 2,
    "decision_proof": DecisionProof,
    "cost_usd": 0.000138,
    "input_tokens": 50,
    "output_tokens": 100
}
```

### Opportunity Model

Each opportunity contains:
- `permit_number`: DOB Job Filing Number
- `job_type`: "NB" or "A1"
- `address`: Construction site address
- `borough`: NYC Borough
- `owner_name`: Property owner
- `estimated_fee`: DOB permit fee (USD)
- `estimated_project_cost`: Total project cost estimate
- `filing_date`: Permit filing date
- `issuance_date`: Permit issuance date
- `opportunity_score`: Scout's confidence (0.0-1.0)

## Veteran Skeptic Filter

The Veteran Skeptic logic ignores permits with estimated fees below $5,000. This focuses resources on high-value projects that justify compliance validation costs.

**Rationale**: Small projects (< $5k fee) typically have minimal insurance requirements and low profit margins. The compliance validation cost may exceed potential revenue from these projects.

## Production Configuration

### Socrata API Token

Set environment variable:
```bash
export NYC_SOCRATA_API_TOKEN="your_token_here"
```

Get a token at: https://data.cityofnewyork.us/profile/app_tokens

### Production Usage

```python
result = find_opportunities(
    hours_lookback=24,
    min_estimated_fee=5000.0,
    job_types=["NB", "A1"],
    use_mock=False  # Use real Socrata API
)
```

## Integration with Guard Agent

Scout hands off opportunities to Guard via AgentHandshakeV2:

```python
# Scout discovers opportunity
scout_result = find_opportunities(use_mock=True)
opportunity = scout_result["opportunities"][0]

# Create handshake
scout_handshake = create_scout_handshake(
    opportunity=opportunity,
    decision_proof_hash=scout_result["decision_proof"].proof_hash,
    target_agent=AgentRole.GUARD
)

# Pass to Guard
from packages.agents.guard.core import validate_coi

guard_result = validate_coi(
    pdf_path=Path("/path/to/coi.pdf"),
    parent_handshake=scout_handshake,
    project_id=opportunity.to_project_id()
)
```

## Testing

Run integration tests:
```bash
pytest tests/integration/test_scout_guard_flow.py -v
```

Run demo:
```bash
python3 demo_scout_guard_workflow.py
```

## Cost Efficiency

Scout is designed for extreme cost efficiency:
- **Per-search cost**: ~$0.000138
- **Token usage**: Minimal (50 input, 100 output)
- **No LLM calls**: Socrata API queries don't use language models
- **Batch processing**: Can process 1000+ permits in single query

Combined Scout + Guard cost: **$0.000763/doc** (well under $0.007 target)

## Architecture

```
Scout Agent
├── Socrata API Client (Mock/Real)
├── Opportunity Parser
├── Veteran Skeptic Filter
├── Decision Proof Generator
└── Handshake Creator
```

## Audit Trail

Scout generates cryptographic audit trails via:
1. **DecisionProof**: SHA-256 hash of discovery logic
2. **AgentHandshakeV2**: Links Scout → Guard with parent hash
3. **AuditChain**: Complete chain verification from discovery to outcome

## Roadmap

- [ ] Real-time permit streaming via Socrata API
- [ ] Machine learning for opportunity scoring
- [ ] Integration with property tax records for project validation
- [ ] Multi-borough parallel discovery
- [ ] Historical trend analysis for lead quality scoring
