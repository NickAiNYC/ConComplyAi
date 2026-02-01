"""Pydantic models for Construction Compliance AI - Type-safe contracts"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class RiskLevel(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class Violation(BaseModel):
    """Single violation detected by vision AI"""
    violation_id: str
    category: str
    description: str
    confidence: float = Field(ge=0.0, le=1.0)
    risk_level: RiskLevel
    estimated_fine: float
    location: str


class PermitData(BaseModel):
    """NYC DOB/HPD permit information"""
    site_id: str
    permit_number: Optional[str]
    status: str
    expiration_date: Optional[datetime]
    violations_on_record: int


class AgentOutput(BaseModel):
    """Standardized agent output for state tracking"""
    agent_name: str
    status: str
    tokens_used: int
    usd_cost: float
    timestamp: datetime
    data: Dict[str, Any]


class ConstructionState(BaseModel):
    """LangGraph state - complete system state"""
    site_id: str
    image_url: Optional[str] = None
    violations: List[Violation] = Field(default_factory=list)
    permit_data: Optional[PermitData] = None
    risk_score: float = 0.0
    estimated_savings: float = 0.0
    agent_outputs: List[AgentOutput] = Field(default_factory=list)
    agent_errors: List[str] = Field(default_factory=list)
    total_tokens: int = 0
    total_cost: float = 0.0
    processing_start: Optional[datetime] = None
    processing_end: Optional[datetime] = None
    
    class Config:
        arbitrary_types_allowed = True
