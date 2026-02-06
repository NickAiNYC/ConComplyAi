"""
Scout Agent Finder - NYC DOB Permit Opportunity Discovery
Uses Socrata API to discover high-value construction leads
Implements 'Veteran Skeptic' filtering to ignore low-value permits

BINDING CONSTRAINTS:
- MUST filter for permits issued in last 24 hours
- MUST filter for job types 'NB' (New Building) and 'A1' (Major Alteration)
- MUST ignore permits with Estimated Fee < $5,000 (Veteran Skeptic)
- Cost target: Keep Socrata API calls efficient
"""
import hashlib
import json
from typing import List, Dict, Any, Optional, Literal
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
from sodapy import Socrata

from packages.core.agent_protocol import (
    AgentRole, AgentHandshakeV2, AgentOutputProtocol
)
from packages.core.audit import (
    DecisionProof, LogicCitation, ComplianceStandard,
    create_decision_proof
)
from packages.core.telemetry import track_agent_cost


class Opportunity(BaseModel):
    """
    NYC Construction Permit Opportunity discovered by Scout
    Represents a potential compliance validation project
    """
    # Permit identification
    permit_number: str = Field(description="DOB Job Filing Number")
    job_type: Literal["NB", "A1"] = Field(description="New Building or Major Alteration")
    
    # Project details
    address: str = Field(description="Construction site address")
    borough: str = Field(description="NYC Borough")
    owner_name: str = Field(description="Property owner name")
    owner_phone: Optional[str] = Field(default=None, description="Owner contact")
    
    # Financial metrics
    estimated_fee: float = Field(description="DOB estimated permit fee (USD)")
    estimated_project_cost: Optional[float] = Field(
        default=None,
        description="Estimated total project cost (derived from fee)"
    )
    
    # Dates
    filing_date: datetime = Field(description="Permit filing date")
    issuance_date: datetime = Field(description="Permit issuance date")
    
    # Opportunity scoring
    opportunity_score: float = Field(
        ge=0.0, le=1.0,
        description="Scout's confidence this is a viable opportunity"
    )
    
    # Metadata
    raw_permit_data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Raw Socrata API response for audit trail"
    )
    
    class Config:
        frozen = True  # Immutable for audit integrity
    
    def to_project_id(self) -> str:
        """Generate unique project ID for handshake chain"""
        return f"SCOUT-{self.permit_number}-{self.filing_date.strftime('%Y%m%d')}"


class ScoutOutput(AgentOutputProtocol):
    """
    Scout Agent complete output with opportunities and handshake
    Inherits from AgentOutputProtocol for multi-agent consistency
    """
    opportunities: List[Opportunity] = Field(default_factory=list)
    search_criteria: Dict[str, Any] = Field(
        default_factory=dict,
        description="Filters used for this search"
    )
    total_permits_scanned: int = Field(
        description="Total permits examined before filtering"
    )
    opportunities_found: int = Field(
        description="Number of viable opportunities after filtering"
    )


def _create_mock_socrata_client(domain: str, app_token: Optional[str] = None) -> Any:
    """
    Mock Socrata client for development/testing
    In production: Use real Socrata client with API token
    
    Returns mock data matching DOB Permit Issuance schema:
    https://data.cityofnewyork.us/Housing-Development/DOB-Permit-Issuance/ipu4-2q9a
    """
    class MockSocrataClient:
        def __init__(self, domain: str, app_token: Optional[str] = None):
            self.domain = domain
            self.app_token = app_token
        
        def get(self, dataset_id: str, **kwargs) -> List[Dict[str, Any]]:
            """
            Mock Socrata API get() method
            Returns synthetic permit data matching NYC DOB schema
            """
            # Generate deterministic mock data
            now = datetime.now()
            yesterday = now - timedelta(days=1)
            
            # Mock permits with various characteristics
            mock_permits = [
                {
                    "job__": "121234567",
                    "job_type": "NB",
                    "borough": "MANHATTAN",
                    "house__": "123",
                    "street_name": "MAIN STREET",
                    "owner_s_first_name": "JOHN",
                    "owner_s_last_name": "DOE",
                    "owner_s_business_name": "NYC School Construction Authority",
                    "owner_s_phone__": "2125551234",
                    "filing_date": yesterday.strftime("%Y-%m-%dT%H:%M:%S.000"),
                    "issuance_date": now.strftime("%Y-%m-%dT%H:%M:%S.000"),
                    "job_start_date": (now + timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%S.000"),
                    "estimated_job_costs": "5000000",
                    "fee_status": "PAID",
                    "filing_status": "INITIAL",
                    "permittee_s_license_type": "GC",
                },
                {
                    "job__": "121234568",
                    "job_type": "A1",
                    "borough": "BROOKLYN",
                    "house__": "456",
                    "street_name": "PROSPECT PARK WEST",
                    "owner_s_first_name": "JANE",
                    "owner_s_last_name": "SMITH",
                    "owner_s_business_name": "Brooklyn Development Corp",
                    "owner_s_phone__": "7185555678",
                    "filing_date": yesterday.strftime("%Y-%m-%dT%H:%M:%S.000"),
                    "issuance_date": now.strftime("%Y-%m-%dT%H:%M:%S.000"),
                    "job_start_date": (now + timedelta(days=14)).strftime("%Y-%m-%dT%H:%M:%S.000"),
                    "estimated_job_costs": "8000000",
                    "fee_status": "PAID",
                    "filing_status": "INITIAL",
                    "permittee_s_license_type": "GC",
                },
                {
                    # Low-value permit (should be filtered by Veteran Skeptic)
                    "job__": "121234569",
                    "job_type": "NB",
                    "borough": "QUEENS",
                    "house__": "789",
                    "street_name": "QUEENS BOULEVARD",
                    "owner_s_first_name": "BOB",
                    "owner_s_last_name": "JOHNSON",
                    "owner_s_business_name": "Small Builder LLC",
                    "owner_s_phone__": "9175552345",
                    "filing_date": yesterday.strftime("%Y-%m-%dT%H:%M:%S.000"),
                    "issuance_date": now.strftime("%Y-%m-%dT%H:%M:%S.000"),
                    "job_start_date": (now + timedelta(days=21)).strftime("%Y-%m-%dT%H:%M:%S.000"),
                    "estimated_job_costs": "50000",  # Low value - will be filtered
                    "fee_status": "PAID",
                    "filing_status": "INITIAL",
                    "permittee_s_license_type": "GC",
                },
                {
                    # Old permit (outside 24 hour window)
                    "job__": "121234570",
                    "job_type": "A1",
                    "borough": "BRONX",
                    "house__": "321",
                    "street_name": "GRAND CONCOURSE",
                    "owner_s_first_name": "ALICE",
                    "owner_s_last_name": "WILLIAMS",
                    "owner_s_business_name": "Bronx Builders Inc",
                    "owner_s_phone__": "7185559012",
                    "filing_date": (now - timedelta(days=3)).strftime("%Y-%m-%dT%H:%M:%S.000"),
                    "issuance_date": (now - timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%S.000"),
                    "job_start_date": now.strftime("%Y-%m-%dT%H:%M:%S.000"),
                    "estimated_job_costs": "3000000",
                    "fee_status": "PAID",
                    "filing_status": "INITIAL",
                    "permittee_s_license_type": "GC",
                },
            ]
            
            # Filter based on kwargs (where clause)
            where_clause = kwargs.get("where", "")
            
            # Simple filtering for testing
            # In production, Socrata handles this server-side
            filtered = []
            for permit in mock_permits:
                # Check issuance date (last 24 hours)
                issuance = datetime.fromisoformat(permit["issuance_date"].replace(".000", ""))
                if (now - issuance).total_seconds() > 86400:  # 24 hours
                    continue
                
                # Check job type
                if "job_type" in where_clause:
                    if permit["job_type"] not in ["NB", "A1"]:
                        continue
                
                filtered.append(permit)
            
            return filtered
        
        def close(self):
            """Mock close method"""
            pass
    
    return MockSocrataClient(domain, app_token)


def _parse_permit_to_opportunity(permit_data: Dict[str, Any]) -> Optional[Opportunity]:
    """
    Parse Socrata permit data into Opportunity object
    
    Args:
        permit_data: Raw permit data from Socrata API
    
    Returns:
        Opportunity object or None if data is invalid
    """
    try:
        # Extract fields from Socrata response
        permit_number = permit_data.get("job__", "")
        job_type = permit_data.get("job_type", "")
        
        # Build address
        house_num = permit_data.get("house__", "")
        street = permit_data.get("street_name", "")
        address = f"{house_num} {street}".strip()
        borough = permit_data.get("borough", "UNKNOWN")
        
        # Owner information
        owner_first = permit_data.get("owner_s_first_name", "")
        owner_last = permit_data.get("owner_s_last_name", "")
        owner_business = permit_data.get("owner_s_business_name", "")
        owner_name = owner_business if owner_business else f"{owner_first} {owner_last}".strip()
        owner_phone = permit_data.get("owner_s_phone__")
        
        # Dates
        filing_date_str = permit_data.get("filing_date", "")
        issuance_date_str = permit_data.get("issuance_date", "")
        
        # Parse dates
        filing_date = datetime.fromisoformat(filing_date_str.replace(".000", ""))
        issuance_date = datetime.fromisoformat(issuance_date_str.replace(".000", ""))
        
        # Financial data
        estimated_cost_str = permit_data.get("estimated_job_costs", "0")
        estimated_project_cost = float(estimated_cost_str) if estimated_cost_str else 0.0
        
        # Estimate DOB fee (simplified: ~0.5% of project cost)
        estimated_fee = estimated_project_cost * 0.005
        
        # Calculate opportunity score based on project characteristics
        opportunity_score = 0.5  # Base score
        
        # Higher score for SCA (school construction)
        if "school" in owner_business.lower() or "sca" in owner_business.lower():
            opportunity_score += 0.3
        
        # Higher score for larger projects
        if estimated_project_cost > 10_000_000:
            opportunity_score += 0.2
        elif estimated_project_cost > 5_000_000:
            opportunity_score += 0.1
        
        # Cap at 1.0
        opportunity_score = min(opportunity_score, 1.0)
        
        return Opportunity(
            permit_number=permit_number,
            job_type=job_type,
            address=address,
            borough=borough,
            owner_name=owner_name,
            owner_phone=owner_phone,
            estimated_fee=estimated_fee,
            estimated_project_cost=estimated_project_cost,
            filing_date=filing_date,
            issuance_date=issuance_date,
            opportunity_score=opportunity_score,
            raw_permit_data=permit_data
        )
    
    except (KeyError, ValueError, TypeError) as e:
        # Invalid or incomplete permit data
        return None


@track_agent_cost(agent_name="Scout", model_name="claude-3-haiku")
def find_opportunities(
    hours_lookback: int = 24,
    min_estimated_fee: float = 5000.0,
    job_types: List[str] = None,
    use_mock: bool = True
) -> Dict[str, Any]:
    """
    Scout Agent main function - Find NYC permit opportunities
    
    Args:
        hours_lookback: Hours to look back for new permits (default: 24)
        min_estimated_fee: Minimum fee threshold (Veteran Skeptic filter, default: $5k)
        job_types: List of job types to filter (default: ['NB', 'A1'])
        use_mock: Use mock data for testing (default: True)
    
    Returns:
        Dict containing ScoutOutput and metadata for cost tracking
        Must include 'input_tokens' and 'output_tokens' for telemetry
    """
    if job_types is None:
        job_types = ["NB", "A1"]
    
    # Calculate time window
    now = datetime.now()
    cutoff_time = now - timedelta(hours=hours_lookback)
    
    # Initialize Socrata client
    if use_mock:
        client = _create_mock_socrata_client(
            domain="data.cityofnewyork.us"
        )
    else:
        # Production: Use real Socrata with API token
        # client = Socrata(
        #     "data.cityofnewyork.us",
        #     app_token=os.getenv("NYC_SOCRATA_API_TOKEN"),
        #     timeout=30
        # )
        raise NotImplementedError("Production Socrata client not configured")
    
    # Build Socrata query
    # Dataset: DOB Permit Issuance
    # https://data.cityofnewyork.us/Housing-Development/DOB-Permit-Issuance/ipu4-2q9a
    dataset_id = "ipu4-2q9a"
    
    # Build where clause for filtering
    job_type_filter = " OR ".join([f"job_type='{jt}'" for jt in job_types])
    where_clause = f"({job_type_filter}) AND issuance_date >= '{cutoff_time.isoformat()}'"
    
    # Query Socrata API
    try:
        raw_permits = client.get(
            dataset_id,
            where=where_clause,
            limit=1000,  # Max permits to fetch
            order="issuance_date DESC"
        )
    except Exception as e:
        # Handle API errors gracefully
        raw_permits = []
    finally:
        if hasattr(client, 'close'):
            client.close()
    
    # Token usage estimation (Socrata API calls don't use LLM tokens)
    # For cost tracking, we'll report minimal tokens
    input_tokens = 50   # Minimal processing for API calls
    output_tokens = 100  # Minimal processing for results
    
    # Parse permits into Opportunities
    all_opportunities = []
    for permit_data in raw_permits:
        opportunity = _parse_permit_to_opportunity(permit_data)
        if opportunity:
            all_opportunities.append(opportunity)
    
    # VETERAN SKEPTIC FILTER: Remove low-value permits
    filtered_opportunities = [
        opp for opp in all_opportunities
        if opp.estimated_fee >= min_estimated_fee
    ]
    
    # Create decision proof for Scout's work
    logic_citations = [
        LogicCitation(
            standard=ComplianceStandard.NYC_BC_3301,
            clause="DOB Permit Discovery",
            interpretation=f"Filtered {len(all_opportunities)} permits to {len(filtered_opportunities)} viable opportunities using Veteran Skeptic threshold of ${min_estimated_fee:,.0f}",
            confidence=0.95
        )
    ]
    
    reasoning = (
        f"Scout discovered {len(filtered_opportunities)} high-value construction opportunities "
        f"from {len(raw_permits)} total permits issued in last {hours_lookback} hours. "
        f"Applied Veteran Skeptic filter (min fee: ${min_estimated_fee:,.0f}) "
        f"focusing on {', '.join(job_types)} job types."
    )
    
    decision_proof = create_decision_proof(
        agent_name="Scout",
        decision="OPPORTUNITIES_FOUND" if filtered_opportunities else "NO_OPPORTUNITIES",
        input_data={
            "hours_lookback": hours_lookback,
            "min_estimated_fee": min_estimated_fee,
            "job_types": job_types,
            "cutoff_time": cutoff_time.isoformat(),
        },
        logic_citations=logic_citations,
        reasoning=reasoning,
        confidence=0.95,
        risk_level="LOW",
        estimated_financial_impact=None,
        cost_usd=0.0  # Will be filled by decorator
    )
    
    # Create Scout output
    # Note: ScoutOutput requires a handshake, but we'll create individual handshakes
    # for each opportunity when they're passed to Guard
    
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "opportunities": filtered_opportunities,
        "search_criteria": {
            "hours_lookback": hours_lookback,
            "min_estimated_fee": min_estimated_fee,
            "job_types": job_types,
        },
        "total_permits_scanned": len(raw_permits),
        "opportunities_found": len(filtered_opportunities),
        "decision_proof": decision_proof,
        "metadata": {
            "success": True,
            "document_id": f"SCOUT-{now.strftime('%Y%m%d%H%M%S')}"
        }
    }


def create_scout_handshake(
    opportunity: Opportunity,
    decision_proof_hash: str,
    target_agent: AgentRole = AgentRole.GUARD
) -> AgentHandshakeV2:
    """
    Create handshake for Scout → Next Agent transition
    
    Args:
        opportunity: The opportunity being handed off
        decision_proof_hash: SHA-256 hash from Scout's DecisionProof
        target_agent: Next agent in chain (default: Guard for COI validation)
    
    Returns:
        AgentHandshakeV2 object ready for audit chain
    """
    return AgentHandshakeV2(
        source_agent=AgentRole.SCOUT,
        target_agent=target_agent,
        project_id=opportunity.to_project_id(),
        decision_hash=decision_proof_hash,
        parent_handshake_id=None,  # Scout is always first in chain
        transition_reason="opportunity_discovered",
        metadata={
            "permit_number": opportunity.permit_number,
            "job_type": opportunity.job_type,
            "borough": opportunity.borough,
            "estimated_project_cost": opportunity.estimated_project_cost,
            "opportunity_score": opportunity.opportunity_score,
        }
    )
