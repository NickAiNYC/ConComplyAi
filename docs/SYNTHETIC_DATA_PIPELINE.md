# Synthetic Data Generation Pipeline

## Overview

The ConComplyAI synthetic data generation pipeline creates realistic construction violation scenarios without requiring real construction site photographs. This ensures privacy compliance while enabling training on edge cases and rare violations.

## Key Benefits

### 1. Privacy Compliance
- **Zero real construction sites photographed**
- No worker faces or identifying information
- GDPR/CCPA compliant by design
- Safe for public datasets and demos

### 2. Edge Case Training
- Generate rare scenarios (85-story scaffolding failures)
- Extreme weather conditions
- Multiple simultaneous violations
- Critical infrastructure edge cases

### 3. Data Augmentation
- 1000+ scenarios per hour
- Deterministic generation with seeds
- Balanced difficulty distribution
- Realistic OSHA/NYC Building Code references

## Quick Start

```python
from core.synthetic_generator import SyntheticViolationGenerator, ViolationType

# Initialize generator with seed for reproducibility
generator = SyntheticViolationGenerator(seed=42)

# Generate a single violation
violation = generator.generate_violation_scenario(
    ViolationType.SCAFFOLDING,
    context={"height": 75, "severity": "immediate collapse"}
)

print(f"ID: {violation['violation_id']}")
print(f"Description: {violation['description']}")
print(f"Risk Level: {violation['risk_level']}")
print(f"Estimated Fine: ${violation['estimated_fine']:,}")
print(f"OSHA Code: {violation['osha_code']}")
```

**Output:**
```
ID: SYNTH-SCAFFOLDING-2679
Description: Unsecured scaffolding on 75-story building, immediate collapse risk
Risk Level: CRITICAL
Estimated Fine: $98,265
OSHA Code: 1926.451
```

## Violation Types

### Supported Categories

| Category | OSHA Code | Risk Levels | Fine Range |
|----------|-----------|-------------|------------|
| Scaffolding | 1926.451 | CRITICAL, HIGH | $15K - $100K |
| Fall Protection | 1926.501 | CRITICAL, HIGH | $20K - $120K |
| PPE | 1926.100 | HIGH, MEDIUM | $3K - $15K |
| Structural Safety | NYC BC 1604 | CRITICAL | $75K - $150K |
| Electrical | 1926.404 | HIGH | $15K - $30K |
| Confined Space | 1926.1203 | HIGH | $20K - $45K |
| Excavation | 1926.651 | CRITICAL | $35K - $75K |
| Debris | 1926.250 | MEDIUM | $2K - $8K |

### Example Scenarios

#### Scaffolding Violations
```python
violation = generator.generate_violation_scenario(
    ViolationType.SCAFFOLDING,
    context={"height": 45}
)

# Possible outputs:
# - "Unsecured scaffolding on 45-story building, immediate collapse risk"
# - "Missing guardrails on scaffold platform at 45ft"
```

#### Fall Protection Violations
```python
violation = generator.generate_violation_scenario(
    ViolationType.FALL_PROTECTION,
    context={"height": 30, "location": "roof perimeter"}
)

# Possible outputs:
# - "Workers at 30ft without harness or safety lines"
# - "Missing edge protection on roof perimeter"
```

## Complete Site Scenarios

### Generate Full Site Data

```python
# Generate a complete construction site with multiple violations
site = generator.generate_construction_site_scenario(
    site_id="DEMO-SITE-001",
    difficulty="hard"
)

print(f"Site ID: {site['site_id']}")
print(f"Difficulty: {site['difficulty']}")
print(f"Building Type: {site['metadata']['building_type']}")
print(f"Construction Phase: {site['metadata']['construction_phase']}")
print(f"Worker Count: {site['metadata']['worker_count']}")
print(f"Violations: {len(site['violations'])}")

# Inspect violations
for v in site['violations']:
    print(f"  - {v['category']}: {v['risk_level']} (${v['estimated_fine']:,})")
```

**Output:**
```
Site ID: DEMO-SITE-001
Difficulty: hard
Building Type: high_rise_residential
Construction Phase: exterior
Worker Count: 23
Violations: 4

  - Scaffolding: CRITICAL ($87,234)
  - Fall Protection: HIGH ($28,500)
  - PPE: MEDIUM ($6,750)
  - Debris: MEDIUM ($4,200)
```

### Difficulty Levels

| Difficulty | Violation Count | Use Case |
|------------|----------------|----------|
| Easy | 0-1 | Baseline testing, low-risk sites |
| Medium | 1-3 | Standard training, typical scenarios |
| Hard | 3-6 | Edge cases, high-risk situations |
| Extreme | 5-10 | Stress testing, disaster scenarios |

```python
# Generate different difficulty levels
easy_site = generator.generate_construction_site_scenario(
    "EASY-001", difficulty="easy"
)

extreme_site = generator.generate_construction_site_scenario(
    "EXTREME-001", difficulty="extreme"
)

print(f"Easy violations: {len(easy_site['violations'])}")
print(f"Extreme violations: {len(extreme_site['violations'])}")
```

## Training Dataset Generation

### Bulk Generation

```python
# Generate 1000 training samples
dataset = generator.generate_training_dataset(
    num_samples=1000,
    difficulty_distribution={
        "easy": 0.2,      # 20% easy cases
        "medium": 0.4,    # 40% medium cases  
        "hard": 0.3,      # 30% hard cases
        "extreme": 0.1    # 10% extreme cases
    }
)

print(f"Generated {len(dataset)} scenarios")

# Statistics
total_violations = sum(len(s['violations']) for s in dataset)
print(f"Total violations: {total_violations}")
print(f"Avg violations per site: {total_violations / len(dataset):.1f}")

# Breakdown by difficulty
for difficulty in ["easy", "medium", "hard", "extreme"]:
    count = sum(1 for s in dataset if s['difficulty'] == difficulty)
    print(f"{difficulty.capitalize()}: {count} sites ({count/len(dataset)*100:.1f}%)")
```

**Output:**
```
Generated 1000 scenarios
Total violations: 2,847
Avg violations per site: 2.8

Easy: 201 sites (20.1%)
Medium: 398 sites (39.8%)
Hard: 304 sites (30.4%)
Extreme: 97 sites (9.7%)
```

### Export for Training

```python
import json

# Generate dataset
dataset = generator.generate_training_dataset(num_samples=500)

# Export to JSON
with open('training_data.json', 'w') as f:
    json.dump(dataset, f, indent=2, default=str)

print(f"Exported {len(dataset)} scenarios to training_data.json")
```

## Deterministic Generation

### Reproducible Results

```python
# Same seed produces same results
gen1 = SyntheticViolationGenerator(seed=123)
gen2 = SyntheticViolationGenerator(seed=123)

site1 = gen1.generate_construction_site_scenario("TEST-001")
site2 = gen2.generate_construction_site_scenario("TEST-001")

# Both will have same metadata and structure
assert site1['difficulty'] == site2['difficulty']
assert site1['metadata']['building_type'] == site2['metadata']['building_type']
```

### Use Cases
- **Unit testing**: Deterministic test fixtures
- **Benchmarking**: Consistent evaluation sets
- **Reproducibility**: Research and validation
- **Demo scenarios**: Controlled demonstrations

## Integration Examples

### With Multi-Agent System

```python
from core.synthetic_generator import SyntheticViolationGenerator
from core.multi_agent_supervisor import run_multi_agent_compliance_check

# Generate synthetic scenario for testing
generator = SyntheticViolationGenerator(seed=42)
scenario = generator.generate_construction_site_scenario(
    "SYNTH-TEST-001",
    difficulty="extreme"
)

print(f"Testing system with {len(scenario['violations'])} synthetic violations")

# In production, synthetic violations would be injected into vision response
# For demo, we just verify the multi-agent system runs
result = run_multi_agent_compliance_check(scenario['site_id'])

print(f"System processed site: {result.site_id}")
print(f"Risk score: {result.risk_score}")
print(f"Agents executed: {len(result.agent_outputs)}")
```

### Augmentation Pipeline

```python
def create_augmented_dataset(base_sites, augmentation_factor=3):
    """
    Augment real site data with synthetic variations
    
    Args:
        base_sites: List of real construction sites
        augmentation_factor: How many synthetic variants per real site
    
    Returns:
        Combined dataset of real + synthetic data
    """
    generator = SyntheticViolationGenerator()
    augmented = list(base_sites)
    
    for site in base_sites:
        # Generate variations
        for i in range(augmentation_factor):
            synthetic_site = generator.generate_construction_site_scenario(
                f"{site['site_id']}-SYNTH-{i}",
                difficulty="medium"
            )
            synthetic_site['augmentation_source'] = site['site_id']
            augmented.append(synthetic_site)
    
    return augmented

# Example usage
real_sites = [...]  # Your real site data
augmented_dataset = create_augmented_dataset(real_sites, augmentation_factor=5)

print(f"Original: {len(real_sites)} sites")
print(f"Augmented: {len(augmented_dataset)} sites ({len(augmented_dataset)/len(real_sites):.1f}x)")
```

## Metadata and Context

### Rich Metadata Generation

Every synthetic site includes comprehensive metadata:

```python
site = generator.generate_construction_site_scenario("META-001")

metadata = site['metadata']
print(f"Building Type: {metadata['building_type']}")
print(f"Construction Phase: {metadata['construction_phase']}")
print(f"Weather: {metadata['weather_conditions']}")
print(f"Time of Day: {metadata['time_of_day']}")
print(f"Worker Count: {metadata['worker_count']}")
print(f"Generation Seed: {metadata['generation_seed']}")
```

**Possible Values:**

- **Building Types**: high_rise_residential, commercial, infrastructure, industrial, mixed_use
- **Construction Phases**: foundation, framing, exterior, interior, finishing
- **Weather**: clear, overcast, light_rain, snow
- **Time of Day**: morning, midday, afternoon, evening
- **Worker Count**: 5-50 workers

### Privacy Markers

All synthetic data includes clear privacy markers:

```python
site = generator.generate_construction_site_scenario("PRIVACY-001")

print(f"Synthetic: {site['synthetic']}")  # True
print(f"Privacy Note: {site['privacy_note']}")
print(f"Purpose: {site['augmentation_purpose']}")
```

## Testing and Validation

### Run Tests

```bash
# Test synthetic data generation
pytest validation/test_synthetic_data.py -v

# Expected: 10/10 tests passing
# - Single violation generation
# - Site scenario generation
# - Violation type coverage
# - Difficulty levels
# - Training dataset generation
# - Deterministic generation
# - Privacy compliance markers
# - OSHA code inclusion
# - Edge case generation
# - Data augmentation purpose
```

### Validation Example

```python
def validate_synthetic_site(site):
    """Validate synthetic site meets requirements"""
    
    # Check required fields
    assert 'site_id' in site
    assert 'violations' in site
    assert 'metadata' in site
    assert site['synthetic'] is True
    
    # Validate violations
    for violation in site['violations']:
        assert 'violation_id' in violation
        assert 'osha_code' in violation
        assert 0.0 <= violation['confidence'] <= 1.0
        assert violation['estimated_fine'] > 0
        assert violation['synthetic'] is True
    
    # Validate metadata
    metadata = site['metadata']
    assert metadata['worker_count'] >= 5
    assert metadata['worker_count'] <= 50
    
    print(f"✓ Site {site['site_id']} validated successfully")

# Validate generated data
site = generator.generate_construction_site_scenario("VAL-001")
validate_synthetic_site(site)
```

## Performance Benchmarks

### Generation Speed

```python
import time

generator = SyntheticViolationGenerator(seed=42)

# Single violation
start = time.time()
for _ in range(1000):
    violation = generator.generate_violation_scenario(ViolationType.SCAFFOLDING)
elapsed = time.time() - start
print(f"Single violations: {1000/elapsed:.0f} per second")

# Complete sites
start = time.time()
for i in range(100):
    site = generator.generate_construction_site_scenario(f"PERF-{i}")
elapsed = time.time() - start
print(f"Complete sites: {100/elapsed:.0f} per second")
```

**Expected Performance:**
- Single violations: ~50,000 per second
- Complete sites: ~10,000 per second
- Training dataset (1000 samples): ~0.1 seconds

## Best Practices

1. **Use seeds for reproducibility**: Critical for testing and benchmarking
2. **Balance difficulty distribution**: Match your real-world data distribution
3. **Include privacy markers**: Always set `synthetic=True` in metadata
4. **Validate OSHA codes**: Ensure codes match violation categories
5. **Export in standard format**: JSON or CSV for ML pipeline compatibility
6. **Version your datasets**: Track which seed and parameters were used
7. **Combine with real data**: 80% real, 20% synthetic for best results
8. **Monitor data drift**: Periodically validate synthetic data matches reality

## Future Enhancements

- **Image generation**: SDXL/ControlNet integration for visual synthetic data
- **Temporal sequences**: Multi-day violation progression scenarios
- **Remediation data**: Synthetic before/after violation correction
- **Regional variations**: Different codes by US state/city
- **Seasonal patterns**: Weather impact on violation types
- **Multi-site scenarios**: Connected violations across multiple sites
