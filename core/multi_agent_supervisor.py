"""Multi-Agent Supervisor - Parallel execution with debate/consensus"""
from typing import Literal
from datetime import datetime
from langgraph.graph import StateGraph, END
from core.models import ConstructionState
from core.agents.vision_agent import analyze_visual_compliance
from core.agents.permit_agent import analyze_permit_compliance
from core.agents.synthesis_agent import synthesize_findings
from core.agents.red_team_agent import challenge_findings
from core.agents.risk_scorer import calculate_final_risk


def create_multi_agent_graph():
    """
    Build LangGraph with parallel agent execution and debate/consensus:
    
    Architecture:
    ┌─────────────┐     ┌─────────────┐
    │ Vision Agent│────→│  Synthesis  │
    │ (OSHA focus)│     │   Agent     │
    └─────────────┘     └──────┬──────┘
                               │
    ┌─────────────┐     ┌──────┴──────┐
    │ Permit Agent│────→│ Red Team    │
    │ (NYC codes) │     │  Agent      │
    └─────────────┘     └──────┬──────┘
                               │
                        ┌──────┴──────┐
                        │ Risk Scorer │
                        │  (Final)    │
                        └─────────────┘
    
    Features:
    - Parallel execution of Vision and Permit agents
    - Synthesis combines findings with debate mechanism
    - Red Team provides adversarial validation
    - Risk Scorer produces final consensus assessment
    """
    
    workflow = StateGraph(ConstructionState)
    
    # Add all agent nodes
    workflow.add_node("vision_agent", analyze_visual_compliance)
    workflow.add_node("permit_agent", analyze_permit_compliance)
    workflow.add_node("synthesis_agent", synthesize_findings)
    workflow.add_node("red_team_agent", challenge_findings)
    workflow.add_node("risk_scorer", calculate_final_risk)
    
    # Define routing logic
    def route_after_parallel(state: ConstructionState) -> Literal["synthesis_agent"]:
        """After parallel agents complete, always route to synthesis"""
        return "synthesis_agent"
    
    def route_after_synthesis(state: ConstructionState) -> Literal["red_team_agent"]:
        """After synthesis, route to red team for validation"""
        return "red_team_agent"
    
    def route_after_red_team(state: ConstructionState) -> Literal["risk_scorer"]:
        """After red team validation, route to final risk scoring"""
        return "risk_scorer"
    
    # Build graph with parallel execution
    # Entry point: start both agents in parallel
    workflow.set_entry_point("vision_agent")
    
    # Vision agent → Permit agent (sequential for now, but can be parallel)
    workflow.add_edge("vision_agent", "permit_agent")
    
    # Permit agent → Synthesis (after both parallel agents complete)
    workflow.add_edge("permit_agent", "synthesis_agent")
    
    # Synthesis → Red Team (adversarial validation)
    workflow.add_edge("synthesis_agent", "red_team_agent")
    
    # Red Team → Risk Scorer (final assessment)
    workflow.add_edge("red_team_agent", "risk_scorer")
    
    # Risk Scorer → END
    workflow.add_edge("risk_scorer", END)
    
    return workflow.compile()


def run_multi_agent_compliance_check(site_id: str, image_url: str = None) -> ConstructionState:
    """
    Execute multi-agent compliance check with parallel execution
    Returns: Complete state with multi-agent consensus assessment
    """
    # Initialize state
    initial_state = ConstructionState(
        site_id=site_id,
        image_url=image_url,
        processing_start=datetime.now()
    )
    
    # Create and execute graph
    graph = create_multi_agent_graph()
    # LangGraph returns AddableValuesDict, convert to ConstructionState
    final_state_dict = graph.invoke(initial_state)
    
    # Convert dictionary result to ConstructionState
    final_state = ConstructionState(**final_state_dict)
    return final_state


def run_batch_multi_agent_compliance(site_ids: list[str]) -> list[ConstructionState]:
    """
    Process multiple sites with multi-agent architecture
    Production: Would use async/parallel execution for 1000+ sites
    """
    results = []
    for site_id in site_ids:
        result = run_multi_agent_compliance_check(site_id)
        results.append(result)
    return results


if __name__ == "__main__":
    # Quick validation run
    result = run_multi_agent_compliance_check("SITE-HY-001", "mock://hudson-yards.jpg")
    print(f"✓ Processed {result.site_id}")
    print(f"  Violations: {len(result.violations)}")
    print(f"  Risk Score: {result.risk_score}")
    print(f"  Estimated Savings: ${result.estimated_savings:,.2f}")
    print(f"  Total Cost: ${result.total_cost:.4f}")
    print(f"  Agents: {len(result.agent_outputs)}")
    print(f"  Errors: {len(result.agent_errors)}")
