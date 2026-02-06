# ConComplyAi Scripts

Utility scripts for maintaining code quality and enforcing Copilot contracts.

## validate_email_tone.py

Validates email templates and broker communication code against ConComplyAi's construction industry tone standards.

### Usage

```bash
# Validate a specific file
python scripts/validate_email_tone.py core/agents/broker_liaison_agent.py

# Validate a directory
python scripts/validate_email_tone.py core/agents/

# Validate email templates directory
python scripts/validate_email_tone.py core/agents/fixer/templates/
```

### Checks Performed

1. **Hemingway Readability Score**: Must be < 10 (high school sophomore level)
2. **Anti-Pattern Detection**: Flags robotic/overly formal language
   - ❌ "I hope this email finds you well"
   - ❌ "As per our previous conversation"
   - ❌ "Please kindly"
   - ❌ "Best regards," (use "Thanks," instead)
3. **Sentence Length**: Max 20 words per sentence
4. **Urgency Markers**: Remediation emails should include specific deadlines

### Requirements

```bash
pip install textstat
```

### Exit Codes

- `0`: All validations passed
- `1`: Critical violations found (will fail CI)

### Integration

This script is automatically run by the `.github/workflows/copilot-contract-enforcement.yml` workflow on every PR that modifies agent code.

## Future Scripts

Planned additions to this directory:

- `copilot_quality_metrics.py` - Track Copilot contract adherence over time
- `validate_agent_handoffs.py` - Verify pre/post-conditions for agent interactions
- `check_decision_proofs.py` - Audit SHA-256 hash generation in decision logs
