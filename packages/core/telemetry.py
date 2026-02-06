"""
Cost Tracking and Telemetry - Decorator for LLM Cost Tracking
Implements $0.007/doc cost validation with CSV audit trail
"""
import os
import csv
import functools
import hashlib
from typing import Callable, Any, Dict, Optional
from datetime import datetime
from pathlib import Path


# OpenAI/Anthropic Pricing (as of 2026)
MODEL_PRICING = {
    # GPT-4o Vision
    "gpt-4o-vision": {
        "input": 0.0000025,   # $2.50 per 1M tokens
        "output": 0.00001,    # $10.00 per 1M tokens
    },
    # Claude 3 Haiku (fast, cheap)
    "claude-3-haiku": {
        "input": 0.00000025,  # $0.25 per 1M tokens
        "output": 0.00000125, # $1.25 per 1M tokens
    },
    # Claude 3.5 Sonnet (balanced)
    "claude-3.5-sonnet": {
        "input": 0.000003,    # $3.00 per 1M tokens
        "output": 0.000015,   # $15.00 per 1M tokens
    },
    # GPT-4 Turbo
    "gpt-4-turbo": {
        "input": 0.00001,     # $10.00 per 1M tokens
        "output": 0.00003,    # $30.00 per 1M tokens
    },
}


def calculate_llm_cost(
    model_name: str,
    input_tokens: int,
    output_tokens: int
) -> float:
    """
    Calculate USD cost of an LLM call based on token usage
    
    Args:
        model_name: Model identifier (e.g., 'claude-3-haiku', 'gpt-4o-vision')
        input_tokens: Number of input/prompt tokens
        output_tokens: Number of completion/output tokens
    
    Returns:
        Total cost in USD
    """
    pricing = MODEL_PRICING.get(model_name, MODEL_PRICING["claude-3-haiku"])
    input_cost = input_tokens * pricing["input"]
    output_cost = output_tokens * pricing["output"]
    return input_cost + output_cost


def track_agent_cost(
    agent_name: str,
    model_name: str = "claude-3-haiku",
    csv_path: str = "benchmarks/runs.csv"
):
    """
    Decorator to track agent LLM costs and save to CSV
    
    Usage:
        @track_agent_cost(agent_name="Guard", model_name="claude-3-haiku")
        def my_agent_function(state):
            # ... agent logic ...
            return {
                "input_tokens": 100,
                "output_tokens": 50,
                # ... other results ...
            }
    
    The decorated function MUST return a dict with 'input_tokens' and 'output_tokens' keys.
    The decorator will automatically add:
        - 'cost_usd': Calculated cost
        - 'agent_name': Agent identifier
        - 'model_name': Model used
        - 'timestamp': ISO timestamp
    
    All metrics are appended to the CSV file specified by csv_path.
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Dict[str, Any]:
            # Execute the agent function
            start_time = datetime.now()
            result = func(*args, **kwargs)
            end_time = datetime.now()
            
            # Extract token usage from result
            input_tokens = result.get("input_tokens", 0)
            output_tokens = result.get("output_tokens", 0)
            
            # Calculate cost
            cost_usd = calculate_llm_cost(model_name, input_tokens, output_tokens)
            
            # Enrich result with cost metrics
            result["cost_usd"] = cost_usd
            result["agent_name"] = agent_name
            result["model_name"] = model_name
            result["timestamp"] = start_time.isoformat()
            result["duration_ms"] = int((end_time - start_time).total_seconds() * 1000)
            
            # Append to CSV
            _append_to_csv(
                csv_path=csv_path,
                agent_name=agent_name,
                model_name=model_name,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_usd=cost_usd,
                timestamp=start_time.isoformat(),
                duration_ms=result["duration_ms"],
                metadata=result.get("metadata", {})
            )
            
            return result
        
        return wrapper
    return decorator


def _append_to_csv(
    csv_path: str,
    agent_name: str,
    model_name: str,
    input_tokens: int,
    output_tokens: int,
    cost_usd: float,
    timestamp: str,
    duration_ms: int,
    metadata: Optional[Dict[str, Any]] = None
):
    """
    Append cost metrics to CSV file (creates file and headers if needed)
    """
    # Ensure directory exists
    csv_file = Path(csv_path)
    csv_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Check if file exists to determine if we need headers
    file_exists = csv_file.exists()
    
    # Prepare row data
    row = {
        "timestamp": timestamp,
        "agent_name": agent_name,
        "model_name": model_name,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
        "cost_usd": f"{cost_usd:.6f}",
        "duration_ms": duration_ms,
        "document_id": metadata.get("document_id", "") if metadata else "",
        "success": metadata.get("success", True) if metadata else True,
    }
    
    # Write to CSV
    with open(csv_file, "a", newline="") as f:
        fieldnames = [
            "timestamp",
            "agent_name", 
            "model_name",
            "input_tokens",
            "output_tokens",
            "total_tokens",
            "cost_usd",
            "duration_ms",
            "document_id",
            "success"
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        
        # Write header if new file
        if not file_exists:
            writer.writeheader()
        
        writer.writerow(row)


def get_cost_summary(csv_path: str = "benchmarks/runs.csv") -> Dict[str, Any]:
    """
    Analyze costs from CSV and return summary statistics
    
    Returns:
        Dict with total cost, average per document, agent breakdown, etc.
    """
    csv_file = Path(csv_path)
    
    if not csv_file.exists():
        return {
            "total_cost_usd": 0.0,
            "total_documents": 0,
            "avg_cost_per_doc": 0.0,
            "meets_target": False,
            "target_cost_per_doc": 0.007,
            "by_agent": {}
        }
    
    # Read CSV and calculate statistics
    total_cost = 0.0
    document_ids = set()
    by_agent = {}
    
    with open(csv_file, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            agent_name = row["agent_name"]
            cost = float(row["cost_usd"])
            doc_id = row.get("document_id", "")
            
            total_cost += cost
            if doc_id:
                document_ids.add(doc_id)
            
            if agent_name not in by_agent:
                by_agent[agent_name] = {
                    "total_cost": 0.0,
                    "num_calls": 0,
                    "total_tokens": 0
                }
            
            by_agent[agent_name]["total_cost"] += cost
            by_agent[agent_name]["num_calls"] += 1
            by_agent[agent_name]["total_tokens"] += int(row.get("total_tokens", 0))
    
    num_docs = len(document_ids) if document_ids else 1  # Avoid division by zero
    avg_cost_per_doc = total_cost / num_docs
    target_cost = 0.007
    
    return {
        "total_cost_usd": round(total_cost, 6),
        "total_documents": len(document_ids),
        "avg_cost_per_doc": round(avg_cost_per_doc, 6),
        "meets_target": avg_cost_per_doc <= target_cost,
        "target_cost_per_doc": target_cost,
        "delta_from_target": round(avg_cost_per_doc - target_cost, 6),
        "by_agent": by_agent
    }


def validate_cost_target(csv_path: str = "benchmarks/runs.csv") -> bool:
    """
    Validate that average cost per document meets $0.007 target
    
    Returns:
        True if cost target is met, False otherwise
    """
    summary = get_cost_summary(csv_path)
    return summary["meets_target"]
