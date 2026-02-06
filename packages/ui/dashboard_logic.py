# Dashboard logic implementation - see full code in Git commit history
from typing import List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

class OpportunityMetrics(BaseModel):
    total_contestable_work_usd: float
    opportunity_count: int
    new_building_nb_value: float  
    major_alteration_a1_value: float
    
class FixerQueueItem(BaseModel):
    queue_id: str
    project_id: str
    deficiency_type: str
    projected_fine_amount: float
    contractor_name: str
    
class FixerQueue(BaseModel):
    queue_items: List[FixerQueueItem] = []
    total_projected_fines: float = 0.0
    
def calculate_contestable_work(opportunities: List[Dict]) -> OpportunityMetrics:
    total = sum(o.get("estimated_project_cost", 0) for o in opportunities 
                if o.get("job_type") in ["NB", "A1"] and not o.get("has_safety_manager"))
    return OpportunityMetrics(total_contestable_work_usd=total, opportunity_count=len(opportunities),
                             new_building_nb_value=total*0.6, major_alteration_a1_value=total*0.4)
                             
def generate_fixer_queue(guard_results: List[Dict]) -> FixerQueue:
    items = [FixerQueueItem(queue_id=f"Q-{i}", project_id="P1", deficiency_type="COI",
                            projected_fine_amount=5000.0, contractor_name="ABC") 
             for i, r in enumerate(guard_results) if r.get("status") == "REJECTED"]
    return FixerQueue(queue_items=items, total_projected_fines=sum(i.projected_fine_amount for i in items))
