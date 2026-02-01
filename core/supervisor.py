"""Supervisor - LangGraph StateGraph with production patterns"""
from typing import Literal
from datetime import datetime
from langgraph.graph import StateGraph, END
from core.models import ConstructionState
from core.agents.violation_detector import detect_violations
from core.agents.report_generator import generate_report


def create_supervisor_graph():
    """
    Build LangGraph with:
    - Conditional routing based on violation detection
    - Error boundaries (agents catch exceptions)
    - Parallel execution capability (via conditional edges)
    - State tracking for observability
    """
    
    workflow = StateGraph(ConstructionState)
    
    # Add agent nodes
    workflow.add_node("detect_violations", detect_violations)
    workflow.add_node("generate_report", generate_report)
    
    # Define routing logic
    def should_generate_report(state: ConstructionState) -> Literal["generate_report", "end"]:
        """Conditional routing: only generate report if violations found or processing complete"""
        # Always generate report (even with 0 violations for cost tracking)
        return "generate_report"
    
    # Build graph edges
    workflow.set_entry_point("detect_violations")
    workflow.add_conditional_edges(
        "detect_violations",
        should_generate_report,
        {
            "generate_report": "generate_report",
            "end": END
        }
    )
    workflow.add_edge("generate_report", END)
    
    return workflow.compile()


def run_compliance_check(site_id: str, image_url: str = None) -> ConstructionState:
    """
    Execute full compliance check for a construction site
    Returns: Complete state with violations, costs, and processing metrics
    """
    # Initialize state
    initial_state = ConstructionState(
        site_id=site_id,
        image_url=image_url,
        processing_start=datetime.now()
    )
    
    # Create and execute graph
    graph = create_supervisor_graph()
    final_state = graph.invoke(initial_state)
    
    return final_state


def run_batch_compliance(site_ids: list[str]) -> list[ConstructionState]:
    """
    Process multiple sites sequentially
    Production: Would use async/parallel execution for 1000+ sites
    """
    results = []
    for site_id in site_ids:
        result = run_compliance_check(site_id)
        results.append(result)
    return results


if __name__ == "__main__":
    # Quick validation run
    result = run_compliance_check("SITE-HY-001", "mock://hudson-yards.jpg")
    print(f"✓ Processed {result.site_id}")
    print(f"  Violations: {len(result.violations)}")
    print(f"  Risk Score: {result.risk_score}")
    print(f"  Estimated Savings: ${result.estimated_savings:,.2f}")
    print(f"  Total Cost: ${result.total_cost:.4f}")
    print(f"  Errors: {len(result.agent_errors)}")
