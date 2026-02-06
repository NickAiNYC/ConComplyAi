"""
Telemetry Service - Real-time Agent Performance Monitoring
Tracks agent flow accuracy, human overrides, token costs, and TTFT metrics.

Complies with 2026-2027 enterprise observability standards.
"""
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
from enum import Enum
import time


class AgentType(str, Enum):
    """Agent types in the multi-agent system"""
    SCOUT = "Scout"  # Vision Agent
    GUARD = "Guard"  # Insurance Validation Agent
    WATCHMAN = "Watchman"  # Sentinel Service
    FIXER = "Fixer"  # Outreach/BrokerLiaison Agent
    FEASIBILITY = "Feasibility"  # Feasibility Agent
    SYNTHESIS = "Synthesis"  # Synthesis Agent
    RED_TEAM = "RedTeam"  # Red Team Agent


class FlowOutcome(str, Enum):
    """Outcome of agent flow execution"""
    SUCCESS_AUTO = "SUCCESS_AUTO"  # Reached goal without human intervention
    SUCCESS_HUMAN = "SUCCESS_HUMAN"  # Reached goal with human intervention
    FAILED = "FAILED"  # Did not reach goal
    ESCALATED = "ESCALATED"  # Escalated to human review


class OverrideReason(str, Enum):
    """Reasons for human override"""
    INCORRECT_CLASSIFICATION = "INCORRECT_CLASSIFICATION"
    MISSED_REQUIREMENT = "MISSED_REQUIREMENT"
    FALSE_POSITIVE = "FALSE_POSITIVE"
    POLICY_EXCEPTION = "POLICY_EXCEPTION"
    QUALITY_ISSUE = "QUALITY_ISSUE"
    OTHER = "OTHER"


class AgentFlowMetric(BaseModel):
    """
    Tracks accuracy of agent flow - % of tasks reaching goal without human intervention
    """
    flow_id: str = Field(description="Unique flow identifier")
    agent_type: AgentType
    started_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    outcome: FlowOutcome
    confidence_score: float = Field(ge=0.0, le=1.0)
    human_intervention_required: bool = Field(default=False)
    intervention_timestamp: Optional[datetime] = None
    task_description: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @property
    def duration_seconds(self) -> Optional[float]:
        """Calculate duration of flow"""
        if self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None


class HumanOverrideEvent(BaseModel):
    """
    Tracks when and why users override agent decisions
    NYC Local Law 144 requires transparency on human-in-the-loop
    """
    override_id: str
    flow_id: str  # Link to AgentFlowMetric
    agent_type: AgentType
    timestamp: datetime = Field(default_factory=datetime.now)
    reason: OverrideReason
    reason_details: str
    original_decision: Dict[str, Any]
    overridden_decision: Dict[str, Any]
    reviewer_id: str
    confidence_before: float = Field(ge=0.0, le=1.0)
    
    # NYC Law 144 compliance fields
    protected_characteristic_involved: bool = Field(
        default=False,
        description="Did override involve protected characteristics?"
    )
    bias_concern_flag: bool = Field(
        default=False,
        description="Was this flagged as potential bias?"
    )


class TokenCostAttribution(BaseModel):
    """
    Real-time cost tracking per agent for budget monitoring
    Maintains $0.007/doc efficiency target
    """
    attribution_id: str
    agent_type: AgentType
    operation_type: str  # e.g., "endorsement_draft", "feasibility_assessment"
    timestamp: datetime = Field(default_factory=datetime.now)
    
    # Token usage
    prompt_tokens: int = Field(ge=0)
    completion_tokens: int = Field(ge=0)
    total_tokens: int = Field(ge=0)
    
    # Cost (USD)
    prompt_cost_usd: float = Field(ge=0.0)
    completion_cost_usd: float = Field(ge=0.0)
    total_cost_usd: float = Field(ge=0.0)
    
    # Model info
    model_name: str = Field(default="claude-3-haiku")
    
    # Efficiency tracking
    meets_target: bool = Field(
        default=True,
        description="Does this meet $0.007/doc target?"
    )
    
    # Context
    document_id: Optional[str] = None
    project_id: Optional[str] = None


class TTFTMetric(BaseModel):
    """
    Time-to-First-Token metric to ensure UI responsiveness
    Target: < 500ms for enterprise UX standards
    """
    metric_id: str
    agent_type: AgentType
    operation_type: str
    timestamp: datetime = Field(default_factory=datetime.now)
    
    # Timing (milliseconds)
    ttft_ms: float = Field(description="Time to first token in milliseconds")
    total_response_time_ms: float
    
    # Target compliance
    meets_target: bool = Field(
        default=True,
        description="Is TTFT < 500ms?"
    )
    
    # Network/infrastructure
    endpoint: str
    region: str = Field(default="us-east-1")


class TelemetryService:
    """
    Central telemetry service for tracking all agent performance metrics
    Provides real-time observability for governance dashboard
    """
    
    def __init__(self):
        self.flow_metrics: List[AgentFlowMetric] = []
        self.override_events: List[HumanOverrideEvent] = []
        self.cost_attributions: List[TokenCostAttribution] = []
        self.ttft_metrics: List[TTFTMetric] = []
        
        # Performance tracking
        self._start_times: Dict[str, float] = {}
    
    def start_flow(
        self,
        flow_id: str,
        agent_type: AgentType,
        task_description: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AgentFlowMetric:
        """Start tracking an agent flow"""
        metric = AgentFlowMetric(
            flow_id=flow_id,
            agent_type=agent_type,
            outcome=FlowOutcome.SUCCESS_AUTO,  # Optimistic default
            confidence_score=1.0,
            task_description=task_description,
            metadata=metadata or {}
        )
        self.flow_metrics.append(metric)
        self._start_times[flow_id] = time.time()
        return metric
    
    def complete_flow(
        self,
        flow_id: str,
        outcome: FlowOutcome,
        confidence_score: float,
        human_intervention: bool = False
    ):
        """Mark flow as completed"""
        for metric in self.flow_metrics:
            if metric.flow_id == flow_id:
                metric.completed_at = datetime.now()
                metric.outcome = outcome
                metric.confidence_score = confidence_score
                metric.human_intervention_required = human_intervention
                if human_intervention:
                    metric.intervention_timestamp = datetime.now()
                break
    
    def record_override(self, override: HumanOverrideEvent):
        """Record a human override event"""
        self.override_events.append(override)
        
        # Update corresponding flow metric
        for metric in self.flow_metrics:
            if metric.flow_id == override.flow_id:
                metric.human_intervention_required = True
                metric.intervention_timestamp = override.timestamp
                metric.outcome = FlowOutcome.SUCCESS_HUMAN
                break
    
    def record_cost(self, cost: TokenCostAttribution):
        """Record token cost attribution"""
        self.cost_attributions.append(cost)
    
    def record_ttft(
        self,
        metric_id: str,
        agent_type: AgentType,
        operation_type: str,
        ttft_ms: float,
        total_ms: float,
        endpoint: str
    ):
        """Record time-to-first-token metric"""
        metric = TTFTMetric(
            metric_id=metric_id,
            agent_type=agent_type,
            operation_type=operation_type,
            ttft_ms=ttft_ms,
            total_response_time_ms=total_ms,
            meets_target=ttft_ms < 500.0,  # 500ms target
            endpoint=endpoint
        )
        self.ttft_metrics.append(metric)
        return metric
    
    def get_agent_flow_accuracy(
        self,
        agent_type: Optional[AgentType] = None,
        time_window_hours: int = 24
    ) -> Dict[str, Any]:
        """
        Calculate agent flow accuracy: % of tasks reaching goal without human intervention
        """
        cutoff = datetime.now() - timedelta(hours=time_window_hours)
        
        # Filter metrics
        metrics = [
            m for m in self.flow_metrics
            if m.started_at >= cutoff
            and (agent_type is None or m.agent_type == agent_type)
            and m.completed_at is not None
        ]
        
        if not metrics:
            return {
                'agent_type': agent_type.value if agent_type else 'ALL',
                'total_flows': 0,
                'accuracy': 0.0,
                'time_window_hours': time_window_hours
            }
        
        # Calculate accuracy
        success_auto = len([m for m in metrics if m.outcome == FlowOutcome.SUCCESS_AUTO])
        total = len(metrics)
        accuracy = (success_auto / total * 100) if total > 0 else 0.0
        
        return {
            'agent_type': agent_type.value if agent_type else 'ALL',
            'total_flows': total,
            'success_auto': success_auto,
            'success_human': len([m for m in metrics if m.outcome == FlowOutcome.SUCCESS_HUMAN]),
            'failed': len([m for m in metrics if m.outcome == FlowOutcome.FAILED]),
            'escalated': len([m for m in metrics if m.outcome == FlowOutcome.ESCALATED]),
            'accuracy_percent': accuracy,
            'human_intervention_rate': len([m for m in metrics if m.human_intervention_required]) / total * 100,
            'time_window_hours': time_window_hours
        }
    
    def get_human_override_rate(
        self,
        agent_type: Optional[AgentType] = None,
        time_window_hours: int = 24
    ) -> Dict[str, Any]:
        """Calculate human-on-the-loop rate"""
        cutoff = datetime.now() - timedelta(hours=time_window_hours)
        
        overrides = [
            o for o in self.override_events
            if o.timestamp >= cutoff
            and (agent_type is None or o.agent_type == agent_type)
        ]
        
        flows = [
            m for m in self.flow_metrics
            if m.started_at >= cutoff
            and (agent_type is None or m.agent_type == agent_type)
        ]
        
        total_flows = len(flows)
        total_overrides = len(overrides)
        
        # Breakdown by reason
        by_reason = {}
        for override in overrides:
            reason = override.reason.value
            by_reason[reason] = by_reason.get(reason, 0) + 1
        
        # Bias concerns (NYC Law 144)
        bias_concerns = len([o for o in overrides if o.bias_concern_flag])
        
        return {
            'agent_type': agent_type.value if agent_type else 'ALL',
            'total_flows': total_flows,
            'total_overrides': total_overrides,
            'override_rate_percent': (total_overrides / total_flows * 100) if total_flows > 0 else 0.0,
            'overrides_by_reason': by_reason,
            'bias_concerns_count': bias_concerns,
            'time_window_hours': time_window_hours
        }
    
    def get_cost_attribution(
        self,
        agent_type: Optional[AgentType] = None,
        time_window_hours: int = 24
    ) -> Dict[str, Any]:
        """Get token cost attribution per agent"""
        cutoff = datetime.now() - timedelta(hours=time_window_hours)
        
        costs = [
            c for c in self.cost_attributions
            if c.timestamp >= cutoff
            and (agent_type is None or c.agent_type == agent_type)
        ]
        
        if not costs:
            return {
                'agent_type': agent_type.value if agent_type else 'ALL',
                'total_operations': 0,
                'total_cost_usd': 0.0,
                'avg_cost_per_operation': 0.0,
                'time_window_hours': time_window_hours
            }
        
        total_cost = sum(c.total_cost_usd for c in costs)
        total_tokens = sum(c.total_tokens for c in costs)
        meeting_target = len([c for c in costs if c.meets_target])
        
        return {
            'agent_type': agent_type.value if agent_type else 'ALL',
            'total_operations': len(costs),
            'total_cost_usd': total_cost,
            'total_tokens': total_tokens,
            'avg_cost_per_operation': total_cost / len(costs),
            'operations_meeting_target': meeting_target,
            'target_compliance_rate': (meeting_target / len(costs) * 100),
            'time_window_hours': time_window_hours
        }
    
    def get_ttft_stats(
        self,
        agent_type: Optional[AgentType] = None,
        time_window_hours: int = 1
    ) -> Dict[str, Any]:
        """Get TTFT statistics"""
        cutoff = datetime.now() - timedelta(hours=time_window_hours)
        
        metrics = [
            m for m in self.ttft_metrics
            if m.timestamp >= cutoff
            and (agent_type is None or m.agent_type == agent_type)
        ]
        
        if not metrics:
            return {
                'agent_type': agent_type.value if agent_type else 'ALL',
                'total_requests': 0,
                'avg_ttft_ms': 0.0,
                'p95_ttft_ms': 0.0,
                'meets_target_rate': 0.0
            }
        
        ttfts = [m.ttft_ms for m in metrics]
        ttfts_sorted = sorted(ttfts)
        p95_index = int(len(ttfts_sorted) * 0.95)
        
        return {
            'agent_type': agent_type.value if agent_type else 'ALL',
            'total_requests': len(metrics),
            'avg_ttft_ms': sum(ttfts) / len(ttfts),
            'min_ttft_ms': min(ttfts),
            'max_ttft_ms': max(ttfts),
            'p95_ttft_ms': ttfts_sorted[p95_index] if ttfts_sorted else 0.0,
            'meets_target_count': len([m for m in metrics if m.meets_target]),
            'meets_target_rate': len([m for m in metrics if m.meets_target]) / len(metrics) * 100,
            'target_ms': 500.0
        }
    
    def get_dashboard_summary(self) -> Dict[str, Any]:
        """Get comprehensive summary for governance dashboard"""
        return {
            'agent_flow_accuracy': {
                agent_type.value: self.get_agent_flow_accuracy(agent_type)
                for agent_type in AgentType
            },
            'human_override_rates': {
                agent_type.value: self.get_human_override_rate(agent_type)
                for agent_type in AgentType
            },
            'cost_attribution': {
                agent_type.value: self.get_cost_attribution(agent_type)
                for agent_type in AgentType
            },
            'ttft_performance': {
                agent_type.value: self.get_ttft_stats(agent_type)
                for agent_type in AgentType
            },
            'overall_accuracy': self.get_agent_flow_accuracy(),
            'overall_override_rate': self.get_human_override_rate(),
            'overall_cost': self.get_cost_attribution(),
            'overall_ttft': self.get_ttft_stats()
        }


# Global singleton instance
_telemetry_service: Optional[TelemetryService] = None


def get_telemetry_service() -> TelemetryService:
    """Get or create global telemetry service instance"""
    global _telemetry_service
    if _telemetry_service is None:
        _telemetry_service = TelemetryService()
    return _telemetry_service
