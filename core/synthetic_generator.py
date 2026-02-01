"""Synthetic Data Generation Pipeline - SDXL/ControlNet style mock generator"""
import random
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
from enum import Enum


class ViolationType(str, Enum):
    """Types of construction violations for synthetic generation"""
    SCAFFOLDING = "scaffolding"
    FALL_PROTECTION = "fall_protection"
    PPE = "ppe"
    STRUCTURAL = "structural"
    ELECTRICAL = "electrical"
    DEBRIS = "debris"
    CONFINED_SPACE = "confined_space"
    EXCAVATION = "excavation"


class SyntheticViolationGenerator:
    """
    Mock SDXL/ControlNet-style synthetic image generator
    Generates realistic construction site violation scenarios
    
    Benefits:
    - Training on edge cases without real data
    - Privacy compliance (no real site photos needed)
    - Data augmentation strategy
    """
    
    def __init__(self, seed: Optional[int] = None):
        self.seed = seed
        if seed is not None:
            random.seed(seed)
        
        # Violation templates for realistic generation
        self.violation_templates = {
            ViolationType.SCAFFOLDING: [
                {
                    "description": "Unsecured scaffolding on {height}-story building, {severity} risk",
                    "confidence_range": (0.85, 0.98),
                    "risk_level": "CRITICAL",
                    "fine_range": (50000, 100000),
                    "osha_code": "1926.451"
                },
                {
                    "description": "Missing guardrails on scaffold platform at {height}ft",
                    "confidence_range": (0.75, 0.92),
                    "risk_level": "HIGH",
                    "fine_range": (15000, 35000),
                    "osha_code": "1926.451(g)"
                }
            ],
            ViolationType.FALL_PROTECTION: [
                {
                    "description": "Workers at {height}ft without harness or safety lines",
                    "confidence_range": (0.88, 0.96),
                    "risk_level": "CRITICAL",
                    "fine_range": (60000, 120000),
                    "osha_code": "1926.501"
                },
                {
                    "description": "Missing edge protection on {location}",
                    "confidence_range": (0.80, 0.94),
                    "risk_level": "HIGH",
                    "fine_range": (20000, 40000),
                    "osha_code": "1926.501(b)"
                }
            ],
            ViolationType.PPE: [
                {
                    "description": "Workers without hard hats in active construction zone",
                    "confidence_range": (0.90, 0.98),
                    "risk_level": "HIGH",
                    "fine_range": (5000, 15000),
                    "osha_code": "1926.100"
                },
                {
                    "description": "Missing safety glasses in demolition area",
                    "confidence_range": (0.82, 0.93),
                    "risk_level": "MEDIUM",
                    "fine_range": (3000, 8000),
                    "osha_code": "1926.102"
                }
            ],
            ViolationType.STRUCTURAL: [
                {
                    "description": "Cracked load-bearing {component} showing {severity} deterioration",
                    "confidence_range": (0.70, 0.88),
                    "risk_level": "CRITICAL",
                    "fine_range": (75000, 150000),
                    "osha_code": "NYC BC 1604"
                }
            ],
            ViolationType.DEBRIS: [
                {
                    "description": "Debris accumulation blocking {location}",
                    "confidence_range": (0.65, 0.85),
                    "risk_level": "MEDIUM",
                    "fine_range": (2000, 8000),
                    "osha_code": "1926.250"
                }
            ],
            ViolationType.ELECTRICAL: [
                {
                    "description": "Exposed electrical wiring at {location}",
                    "confidence_range": (0.78, 0.92),
                    "risk_level": "HIGH",
                    "fine_range": (15000, 30000),
                    "osha_code": "1926.404"
                }
            ],
            ViolationType.CONFINED_SPACE: [
                {
                    "description": "Confined space entry without proper ventilation at {location}",
                    "confidence_range": (0.72, 0.88),
                    "risk_level": "HIGH",
                    "fine_range": (20000, 45000),
                    "osha_code": "1926.1203"
                }
            ],
            ViolationType.EXCAVATION: [
                {
                    "description": "Unprotected excavation trench at {height}ft depth",
                    "confidence_range": (0.80, 0.94),
                    "risk_level": "CRITICAL",
                    "fine_range": (35000, 75000),
                    "osha_code": "1926.651"
                }
            ]
        }
    
    def generate_violation_scenario(
        self, 
        violation_type: ViolationType,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate a single synthetic violation scenario
        
        Args:
            violation_type: Type of violation to generate
            context: Optional context (building height, location, etc.)
        
        Returns:
            Synthetic violation data with realistic parameters
        """
        if context is None:
            context = {}
        
        # Select random template for violation type
        templates = self.violation_templates.get(violation_type, [])
        if not templates:
            raise ValueError(f"No templates for violation type: {violation_type}")
        
        template = random.choice(templates)
        
        # Generate context-specific details
        height = context.get("height", random.randint(20, 85))
        location = context.get("location", random.choice([
            "roof perimeter", "exterior facade", "stairwell", "ground level",
            "floor 12", "loading dock", "excavation site"
        ]))
        severity = context.get("severity", random.choice([
            "immediate collapse", "structural failure", "fall hazard", "injury"
        ]))
        component = context.get("component", random.choice([
            "column", "beam", "foundation wall", "support structure"
        ]))
        
        # Fill in template
        description = template["description"].format(
            height=height,
            location=location,
            severity=severity,
            component=component
        )
        
        # Generate realistic confidence score
        conf_min, conf_max = template["confidence_range"]
        confidence = random.uniform(conf_min, conf_max)
        
        # Generate realistic fine amount
        fine_min, fine_max = template["fine_range"]
        fine = random.randint(fine_min, fine_max)
        
        return {
            "violation_id": f"SYNTH-{violation_type.value.upper()}-{random.randint(1000, 9999)}",
            "category": violation_type.value.replace("_", " ").title(),
            "description": description,
            "confidence": round(confidence, 2),
            "risk_level": template["risk_level"],
            "estimated_fine": fine,
            "location": location,
            "osha_code": template.get("osha_code", "N/A"),
            "synthetic": True,
            "generation_timestamp": datetime.now().isoformat()
        }
    
    def generate_construction_site_scenario(
        self,
        site_id: str,
        violation_count: int = None,
        difficulty: str = "medium"
    ) -> Dict[str, Any]:
        """
        Generate a complete synthetic construction site scenario
        
        Args:
            site_id: Unique site identifier
            violation_count: Number of violations (random if None)
            difficulty: Edge case difficulty (easy, medium, hard, extreme)
        
        Returns:
            Complete synthetic site data with violations
        """
        # Determine violation count based on difficulty
        if violation_count is None:
            difficulty_ranges = {
                "easy": (0, 1),
                "medium": (1, 3),
                "hard": (3, 6),
                "extreme": (5, 10)
            }
            min_v, max_v = difficulty_ranges.get(difficulty, (1, 3))
            violation_count = random.randint(min_v, max_v)
        
        # Select violation types
        available_types = list(ViolationType)
        selected_types = random.sample(
            available_types, 
            min(violation_count, len(available_types))
        )
        
        # Generate violations
        violations = []
        for v_type in selected_types:
            context = {
                "height": random.randint(10, 100),
                "location": f"Zone {random.randint(1, 5)}"
            }
            violation = self.generate_violation_scenario(v_type, context)
            violations.append(violation)
        
        # Generate site metadata
        site_data = {
            "site_id": site_id,
            "synthetic": True,
            "difficulty": difficulty,
            "violations": violations,
            "metadata": {
                "building_type": random.choice([
                    "high_rise_residential", "commercial", "infrastructure",
                    "industrial", "mixed_use"
                ]),
                "construction_phase": random.choice([
                    "foundation", "framing", "exterior", "interior", "finishing"
                ]),
                "weather_conditions": random.choice([
                    "clear", "overcast", "light_rain", "snow"
                ]),
                "time_of_day": random.choice([
                    "morning", "midday", "afternoon", "evening"
                ]),
                "worker_count": random.randint(5, 50),
                "generation_seed": self.seed
            },
            "privacy_note": "Synthetic data - no real construction sites photographed",
            "augmentation_purpose": "Edge case training and privacy compliance"
        }
        
        return site_data
    
    def generate_training_dataset(
        self,
        num_samples: int = 100,
        difficulty_distribution: Optional[Dict[str, float]] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate a complete training dataset of synthetic scenarios
        
        Args:
            num_samples: Number of synthetic samples to generate
            difficulty_distribution: Distribution of difficulties (defaults to balanced)
        
        Returns:
            List of synthetic site scenarios
        """
        if difficulty_distribution is None:
            difficulty_distribution = {
                "easy": 0.2,
                "medium": 0.4,
                "hard": 0.3,
                "extreme": 0.1
            }
        
        dataset = []
        for i in range(num_samples):
            # Select difficulty based on distribution
            rand = random.random()
            cumulative = 0
            difficulty = "medium"
            for diff, prob in difficulty_distribution.items():
                cumulative += prob
                if rand < cumulative:
                    difficulty = diff
                    break
            
            # Generate scenario
            site_id = f"SYNTH-TRAIN-{i:05d}"
            scenario = self.generate_construction_site_scenario(
                site_id=site_id,
                difficulty=difficulty
            )
            dataset.append(scenario)
        
        return dataset


def demonstrate_synthetic_generation():
    """Demonstrate synthetic data generation capabilities"""
    print("=" * 80)
    print("SYNTHETIC DATA GENERATION DEMO")
    print("=" * 80)
    
    generator = SyntheticViolationGenerator(seed=42)
    
    # Generate single violation
    print("\n1. Single Violation Generation:")
    violation = generator.generate_violation_scenario(ViolationType.SCAFFOLDING)
    print(json.dumps(violation, indent=2))
    
    # Generate complete site scenario
    print("\n2. Complete Site Scenario (Hard Difficulty):")
    site = generator.generate_construction_site_scenario(
        site_id="DEMO-SITE-001",
        difficulty="hard"
    )
    print(f"Site: {site['site_id']}")
    print(f"Violations: {len(site['violations'])}")
    print(f"Building Type: {site['metadata']['building_type']}")
    print(f"Privacy Compliant: {site['privacy_note']}")
    
    # Generate small training dataset
    print("\n3. Training Dataset Generation (10 samples):")
    dataset = generator.generate_training_dataset(num_samples=10)
    print(f"Generated {len(dataset)} synthetic scenarios")
    
    # Statistics
    total_violations = sum(len(s['violations']) for s in dataset)
    difficulties = [s['difficulty'] for s in dataset]
    print(f"Total violations: {total_violations}")
    print(f"Difficulty distribution: {dict((d, difficulties.count(d)) for d in set(difficulties))}")
    
    print("\n" + "=" * 80)
    print("Benefits: Edge case training, privacy compliance, data augmentation")
    print("=" * 80)


if __name__ == "__main__":
    demonstrate_synthetic_generation()
