"""Model Registry - A/B testing for cost vs accuracy optimization"""
from typing import Dict, Any
from dataclasses import dataclass


@dataclass
class ModelSpec:
    """Model specification with cost and accuracy metrics"""
    name: str
    cost_per_1k_tokens: float
    accuracy: float
    latency_ms: int


class ModelRegistry:
    """
    Advanced Feature: Multi-model routing based on budget constraints
    Routes low-budget sites to cheaper models, high-value sites to premium models
    """
    
    MODELS = {
        "gpt-4o": ModelSpec(
            name="gpt-4o",
            cost_per_1k_tokens=0.010,
            accuracy=0.92,
            latency_ms=800
        ),
        "claude-3.5": ModelSpec(
            name="claude-3.5-sonnet",
            cost_per_1k_tokens=0.008,
            accuracy=0.89,
            latency_ms=600
        ),
        "gpt-4o-mini": ModelSpec(
            name="gpt-4o-mini",
            cost_per_1k_tokens=0.0015,
            accuracy=0.85,
            latency_ms=400
        )
    }
    
    def select_model(self, budget: float, min_accuracy: float = 0.87) -> ModelSpec:
        """
        Select optimal model based on budget and accuracy requirements
        
        Args:
            budget: Maximum cost per site in USD
            min_accuracy: Minimum required accuracy (default 87%)
        
        Returns:
            ModelSpec that meets requirements, or None if impossible
        """
        # Filter models that meet accuracy requirement
        viable_models = [
            model for model in self.MODELS.values()
            if model.accuracy >= min_accuracy
        ]
        
        if not viable_models:
            # Fallback: return cheapest model if no models meet accuracy
            return min(self.MODELS.values(), key=lambda m: m.cost_per_1k_tokens)
        
        # Estimate 2500 tokens per site (1500 input + 1000 output)
        estimated_tokens = 2500
        
        # Find cheapest model within budget
        affordable_models = [
            model for model in viable_models
            if (model.cost_per_1k_tokens * estimated_tokens / 1000) <= budget
        ]
        
        if affordable_models:
            # Return highest accuracy model within budget
            return max(affordable_models, key=lambda m: m.accuracy)
        
        # If nothing fits budget, return cheapest viable model
        return min(viable_models, key=lambda m: m.cost_per_1k_tokens)
    
    def get_model_choice_log(self, model: ModelSpec, budget: float) -> Dict[str, Any]:
        """Generate log entry for model selection decision"""
        return {
            "selected_model": model.name,
            "cost_per_1k_tokens": model.cost_per_1k_tokens,
            "accuracy": model.accuracy,
            "budget_usd": budget,
            "estimated_cost": (model.cost_per_1k_tokens * 2.5),  # 2500 tokens
            "within_budget": (model.cost_per_1k_tokens * 2.5) <= budget
        }


# Global registry instance
model_registry = ModelRegistry()
