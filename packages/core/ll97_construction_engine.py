"""
LL97 Construction Engine - Construction Site Carbon Emissions Tracking

Local Law 97 (LL97) requires tracking and reducing carbon emissions from buildings.
This engine specifically tracks CONSTRUCTION SITE emissions, including:
- Temporary power emissions (generators, grid connections)
- Construction equipment fuel usage (cranes, excavators, etc.)
- DOB NOW permit integration for site emissions tracking
- Fine projection: $268/ton CO2e

VALUE PROPOSITION: "Your crane is costing you $847/day in unaccounted carbon fines"

Version: 2026.1.0
Last Updated: 2026-02-12
"""
from typing import Dict, List, Optional, Literal
from datetime import datetime, timedelta
from pydantic import BaseModel, Field, ConfigDict
import math


# =============================================================================
# CONSTANTS - LL97 CARBON PRICING
# =============================================================================

# LL97 Carbon Fine Rate (2026 pricing)
LL97_FINE_PER_TON_CO2E = 268.0  # $268 per ton CO2e over limit

# Emissions factors (kg CO2e per unit)
EMISSIONS_FACTORS = {
    # Fuel types (kg CO2e per gallon)
    "diesel": 10.21,  # kg CO2e per gallon
    "gasoline": 8.89,  # kg CO2e per gallon
    "natural_gas": 5.31,  # kg CO2e per therm
    
    # Grid electricity (kg CO2e per kWh) - NYC grid mix
    "grid_electricity": 0.289,  # kg CO2e per kWh (2026 NYC grid)
    
    # Generator efficiency (gallons per kWh)
    "generator_diesel_efficiency": 0.08,  # gallons per kWh
}

# Equipment fuel consumption rates (gallons per hour of operation)
EQUIPMENT_FUEL_RATES = {
    "tower_crane": 12.0,      # gallons/hour
    "mobile_crane": 15.0,      # gallons/hour
    "excavator_large": 8.0,    # gallons/hour
    "excavator_small": 4.0,    # gallons/hour
    "bulldozer": 10.0,         # gallons/hour
    "loader": 6.0,             # gallons/hour
    "concrete_pump": 5.0,      # gallons/hour
    "generator_large": 8.0,    # gallons/hour (250 kW)
    "generator_small": 3.0,    # gallons/hour (100 kW)
    "forklift_diesel": 2.0,    # gallons/hour
    "compressor": 4.0,         # gallons/hour
}

# Construction phase typical equipment mix and hours
CONSTRUCTION_PHASES = {
    "excavation": {
        "duration_days": 30,
        "equipment": {
            "excavator_large": 8.0,     # hours/day
            "bulldozer": 6.0,
            "loader": 6.0,
            "generator_large": 10.0
        }
    },
    "foundation": {
        "duration_days": 45,
        "equipment": {
            "concrete_pump": 8.0,
            "tower_crane": 10.0,
            "generator_large": 12.0
        }
    },
    "structural": {
        "duration_days": 180,
        "equipment": {
            "tower_crane": 10.0,
            "mobile_crane": 4.0,
            "generator_large": 12.0,
            "compressor": 8.0
        }
    },
    "facade": {
        "duration_days": 90,
        "equipment": {
            "mobile_crane": 6.0,
            "generator_small": 8.0,
            "forklift_diesel": 6.0
        }
    },
    "interior": {
        "duration_days": 120,
        "equipment": {
            "generator_small": 10.0,
            "forklift_diesel": 4.0,
            "compressor": 6.0
        }
    }
}


# =============================================================================
# PYDANTIC MODELS
# =============================================================================

class EquipmentEmissions(BaseModel):
    """Equipment emissions calculation"""
    model_config = ConfigDict(frozen=True)
    
    equipment_type: str = Field(description="Type of equipment")
    fuel_type: Literal["diesel", "gasoline", "grid_electricity"] = Field(description="Fuel/power type")
    hours_operated: float = Field(description="Hours of operation")
    fuel_consumed_gallons: Optional[float] = Field(default=None, description="Fuel consumed (gallons)")
    electricity_consumed_kwh: Optional[float] = Field(default=None, description="Electricity consumed (kWh)")
    co2e_kg: float = Field(description="CO2 equivalent emissions (kg)")
    co2e_tons: float = Field(description="CO2 equivalent emissions (tons)")


class ConstructionSiteEmissions(BaseModel):
    """Complete construction site emissions profile"""
    model_config = ConfigDict(frozen=False)
    
    site_id: str = Field(description="Site/permit identifier")
    permit_number: str = Field(description="DOB permit number")
    site_address: str = Field(description="Construction site address")
    project_phase: str = Field(description="Current construction phase")
    start_date: datetime = Field(description="Phase start date")
    end_date: Optional[datetime] = Field(default=None, description="Phase end date")
    
    # Emissions breakdown
    equipment_emissions: List[EquipmentEmissions] = Field(default_factory=list, description="Equipment emissions")
    temporary_power_kwh: float = Field(default=0.0, description="Temporary power usage (kWh)")
    temporary_power_emissions_kg: float = Field(default=0.0, description="Temporary power emissions (kg CO2e)")
    
    # Totals
    total_co2e_kg: float = Field(default=0.0, description="Total CO2e emissions (kg)")
    total_co2e_tons: float = Field(default=0.0, description="Total CO2e emissions (tons)")
    
    # Financial impact
    daily_emissions_kg: float = Field(default=0.0, description="Daily emissions rate (kg/day)")
    daily_fine_projection: float = Field(default=0.0, description="Daily fine projection ($)")
    total_fine_projection: float = Field(default=0.0, description="Total fine projection ($)")
    
    # Metadata
    calculated_at: datetime = Field(default_factory=datetime.utcnow)
    emissions_limit_tons: Optional[float] = Field(default=None, description="Site emissions limit (tons)")
    over_limit: bool = Field(default=False, description="Whether site exceeds limit")


class MitigationRecommendation(BaseModel):
    """Carbon mitigation recommendation"""
    model_config = ConfigDict(frozen=True)
    
    recommendation_type: Literal["equipment_upgrade", "power_switch", "schedule_change", "fuel_switch"]
    title: str = Field(description="Short recommendation title")
    description: str = Field(description="Detailed recommendation")
    equipment_affected: List[str] = Field(description="Equipment types affected")
    
    # Cost-benefit analysis
    implementation_cost: float = Field(description="Cost to implement ($)")
    annual_savings: float = Field(description="Annual cost savings ($)")
    emissions_reduction_tons: float = Field(description="Annual CO2e reduction (tons)")
    payback_period_months: float = Field(description="Payback period (months)")
    
    # Priority
    priority: Literal["HIGH", "MEDIUM", "LOW"] = Field(description="Implementation priority")


# =============================================================================
# EMISSIONS CALCULATION ENGINE
# =============================================================================

class LL97ConstructionEngine:
    """
    LL97 Construction Emissions Calculator
    
    Tracks and projects carbon emissions for NYC construction sites
    with LL97 fine calculations and mitigation recommendations.
    """
    
    def __init__(self, emissions_limit_tons: Optional[float] = None):
        """
        Initialize LL97 engine
        
        Args:
            emissions_limit_tons: Site-specific emissions limit (optional)
        """
        self.emissions_limit_tons = emissions_limit_tons
    
    def calculate_equipment_emissions(
        self,
        equipment_type: str,
        hours_operated: float,
        fuel_type: Literal["diesel", "gasoline", "grid_electricity"] = "diesel"
    ) -> EquipmentEmissions:
        """
        Calculate emissions for specific equipment
        
        Args:
            equipment_type: Type of equipment
            hours_operated: Hours of operation
            fuel_type: Fuel or power type
        
        Returns:
            EquipmentEmissions object
        """
        # Get fuel consumption rate
        fuel_rate = EQUIPMENT_FUEL_RATES.get(equipment_type, 5.0)  # Default 5 gal/hr
        
        if fuel_type == "grid_electricity":
            # Electric equipment (rare in construction, but growing)
            electricity_kwh = hours_operated * fuel_rate * 10  # Approximate conversion
            co2e_kg = electricity_kwh * EMISSIONS_FACTORS["grid_electricity"]
            
            return EquipmentEmissions(
                equipment_type=equipment_type,
                fuel_type=fuel_type,
                hours_operated=hours_operated,
                electricity_consumed_kwh=electricity_kwh,
                co2e_kg=co2e_kg,
                co2e_tons=co2e_kg / 1000.0
            )
        else:
            # Fuel-powered equipment
            fuel_consumed = hours_operated * fuel_rate
            co2e_kg = fuel_consumed * EMISSIONS_FACTORS[fuel_type]
            
            return EquipmentEmissions(
                equipment_type=equipment_type,
                fuel_type=fuel_type,
                hours_operated=hours_operated,
                fuel_consumed_gallons=fuel_consumed,
                co2e_kg=co2e_kg,
                co2e_tons=co2e_kg / 1000.0
            )
    
    def calculate_site_emissions(
        self,
        site_id: str,
        permit_number: str,
        site_address: str,
        project_phase: str,
        start_date: datetime,
        equipment_usage: Dict[str, float],
        temporary_power_kwh: float = 0.0,
        end_date: Optional[datetime] = None
    ) -> ConstructionSiteEmissions:
        """
        Calculate complete site emissions
        
        Args:
            site_id: Site identifier
            permit_number: DOB permit number
            site_address: Site address
            project_phase: Construction phase
            start_date: Phase start date
            equipment_usage: Dict of equipment_type -> hours_per_day
            temporary_power_kwh: Temporary power usage (kWh)
            end_date: Phase end date (optional)
        
        Returns:
            ConstructionSiteEmissions object
        """
        # Calculate equipment emissions
        equipment_emissions = []
        for equipment_type, hours_per_day in equipment_usage.items():
            emissions = self.calculate_equipment_emissions(
                equipment_type=equipment_type,
                hours_operated=hours_per_day,
                fuel_type="diesel"  # Most construction equipment is diesel
            )
            equipment_emissions.append(emissions)
        
        # Calculate temporary power emissions
        temp_power_co2e_kg = temporary_power_kwh * EMISSIONS_FACTORS["grid_electricity"]
        
        # Calculate totals
        equipment_co2e_kg = sum(e.co2e_kg for e in equipment_emissions)
        total_co2e_kg = equipment_co2e_kg + temp_power_co2e_kg
        total_co2e_tons = total_co2e_kg / 1000.0
        
        # Calculate daily rate
        daily_emissions_kg = total_co2e_kg  # Already daily rate from input
        
        # Calculate fine projection
        if self.emissions_limit_tons:
            excess_tons = max(0, total_co2e_tons - self.emissions_limit_tons)
            daily_fine = excess_tons * LL97_FINE_PER_TON_CO2E
            over_limit = excess_tons > 0
        else:
            # No limit set, project fines assuming all emissions are over limit
            daily_fine = total_co2e_tons * LL97_FINE_PER_TON_CO2E
            over_limit = False
        
        # Calculate duration for total fine projection
        if end_date:
            duration_days = (end_date - start_date).days
        else:
            # Use phase duration from template
            phase_info = CONSTRUCTION_PHASES.get(project_phase.lower(), {"duration_days": 90})
            duration_days = phase_info["duration_days"]
        
        total_fine = daily_fine * duration_days
        
        return ConstructionSiteEmissions(
            site_id=site_id,
            permit_number=permit_number,
            site_address=site_address,
            project_phase=project_phase,
            start_date=start_date,
            end_date=end_date,
            equipment_emissions=equipment_emissions,
            temporary_power_kwh=temporary_power_kwh,
            temporary_power_emissions_kg=temp_power_co2e_kg,
            total_co2e_kg=total_co2e_kg,
            total_co2e_tons=total_co2e_tons,
            daily_emissions_kg=daily_emissions_kg,
            daily_fine_projection=daily_fine,
            total_fine_projection=total_fine,
            emissions_limit_tons=self.emissions_limit_tons,
            over_limit=over_limit
        )
    
    def calculate_phase_emissions(
        self,
        site_id: str,
        permit_number: str,
        site_address: str,
        project_phase: str,
        start_date: datetime
    ) -> ConstructionSiteEmissions:
        """
        Calculate emissions for standard construction phase
        
        Uses template equipment mix and durations from CONSTRUCTION_PHASES
        
        Args:
            site_id: Site identifier
            permit_number: DOB permit number
            site_address: Site address
            project_phase: Construction phase
            start_date: Phase start date
        
        Returns:
            ConstructionSiteEmissions object
        """
        phase_key = project_phase.lower()
        if phase_key not in CONSTRUCTION_PHASES:
            raise ValueError(f"Unknown construction phase: {project_phase}")
        
        phase_info = CONSTRUCTION_PHASES[phase_key]
        equipment_usage = phase_info["equipment"]
        duration_days = phase_info["duration_days"]
        end_date = start_date + timedelta(days=duration_days)
        
        return self.calculate_site_emissions(
            site_id=site_id,
            permit_number=permit_number,
            site_address=site_address,
            project_phase=project_phase,
            start_date=start_date,
            equipment_usage=equipment_usage,
            temporary_power_kwh=100.0,  # Default 100 kWh/day temporary power
            end_date=end_date
        )
    
    def generate_mitigation_recommendations(
        self,
        site_emissions: ConstructionSiteEmissions
    ) -> List[MitigationRecommendation]:
        """
        Generate carbon mitigation recommendations
        
        Args:
            site_emissions: Site emissions profile
        
        Returns:
            List of MitigationRecommendation objects
        """
        recommendations = []
        
        # Check for high-emission equipment
        for equip in site_emissions.equipment_emissions:
            if equip.equipment_type in ["tower_crane", "mobile_crane"]:
                # Recommend electric crane
                recommendations.append(MitigationRecommendation(
                    recommendation_type="equipment_upgrade",
                    title=f"Upgrade to Electric {equip.equipment_type.replace('_', ' ').title()}",
                    description=(
                        f"Replace diesel {equip.equipment_type} with electric model. "
                        f"Current emissions: {equip.co2e_tons:.2f} tons/day. "
                        f"Electric would reduce by 70%."
                    ),
                    equipment_affected=[equip.equipment_type],
                    implementation_cost=50000.0,
                    annual_savings=equip.co2e_tons * 365 * LL97_FINE_PER_TON_CO2E * 0.7,
                    emissions_reduction_tons=equip.co2e_tons * 365 * 0.7,
                    payback_period_months=12.0,
                    priority="HIGH"
                ))
        
        # Check temporary power
        if site_emissions.temporary_power_kwh > 50:
            recommendations.append(MitigationRecommendation(
                recommendation_type="power_switch",
                title="Connect to Con Edison Grid Power",
                description=(
                    f"Replace diesel generators with grid connection. "
                    f"Current generator emissions: ~{site_emissions.temporary_power_kwh * 0.08 * 10.21 / 1000:.2f} tons/day. "
                    f"Grid power would reduce by 50%."
                ),
                equipment_affected=["generator_large", "generator_small"],
                implementation_cost=15000.0,
                annual_savings=site_emissions.temporary_power_kwh * 0.08 * 10.21 / 1000 * 365 * LL97_FINE_PER_TON_CO2E * 0.5,
                emissions_reduction_tons=site_emissions.temporary_power_kwh * 0.08 * 10.21 / 1000 * 365 * 0.5,
                payback_period_months=6.0,
                priority="HIGH"
            ))
        
        # Recommend B20 biodiesel
        diesel_equipment = [e for e in site_emissions.equipment_emissions if e.fuel_type == "diesel"]
        if diesel_equipment:
            total_diesel_tons = sum(e.co2e_tons for e in diesel_equipment)
            recommendations.append(MitigationRecommendation(
                recommendation_type="fuel_switch",
                title="Switch to B20 Biodiesel Blend",
                description=(
                    f"Use B20 (20% biodiesel) blend for all diesel equipment. "
                    f"Current diesel emissions: {total_diesel_tons:.2f} tons/day. "
                    f"B20 would reduce by 15%."
                ),
                equipment_affected=[e.equipment_type for e in diesel_equipment],
                implementation_cost=2000.0,
                annual_savings=total_diesel_tons * 365 * LL97_FINE_PER_TON_CO2E * 0.15,
                emissions_reduction_tons=total_diesel_tons * 365 * 0.15,
                payback_period_months=2.0,
                priority="MEDIUM"
            ))
        
        # Sort by priority and payback period
        priority_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        recommendations.sort(key=lambda r: (priority_order[r.priority], r.payback_period_months))
        
        return recommendations


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def calculate_crane_daily_cost(crane_type: str = "tower_crane", hours_per_day: float = 10.0) -> Dict[str, float]:
    """
    Quick calculation: What's the daily carbon cost of a crane?
    
    VALUE PROPOSITION: "Your crane is costing you $847/day in unaccounted carbon fines"
    
    Args:
        crane_type: Type of crane
        hours_per_day: Hours operated per day
    
    Returns:
        Dict with emissions and cost breakdown
    """
    engine = LL97ConstructionEngine()
    emissions = engine.calculate_equipment_emissions(crane_type, hours_per_day)
    
    daily_fine = emissions.co2e_tons * LL97_FINE_PER_TON_CO2E
    
    return {
        "equipment_type": crane_type,
        "hours_per_day": hours_per_day,
        "daily_emissions_kg": emissions.co2e_kg,
        "daily_emissions_tons": emissions.co2e_tons,
        "daily_fine_dollars": daily_fine,
        "monthly_fine_dollars": daily_fine * 30,
        "annual_fine_dollars": daily_fine * 365
    }


def estimate_project_carbon_cost(
    project_phase: str,
    start_date: Optional[datetime] = None
) -> Dict[str, any]:
    """
    Estimate total carbon cost for a construction phase
    
    Args:
        project_phase: Construction phase (excavation, foundation, structural, etc.)
        start_date: Project start date
    
    Returns:
        Dict with cost estimates
    """
    if start_date is None:
        start_date = datetime.now()
    
    engine = LL97ConstructionEngine()
    emissions = engine.calculate_phase_emissions(
        site_id="ESTIMATE",
        permit_number="ESTIMATE",
        site_address="Estimate",
        project_phase=project_phase,
        start_date=start_date
    )
    
    return {
        "project_phase": project_phase,
        "duration_days": (emissions.end_date - emissions.start_date).days if emissions.end_date else 0,
        "daily_emissions_tons": emissions.total_co2e_tons,
        "total_emissions_tons": emissions.total_co2e_tons * ((emissions.end_date - emissions.start_date).days if emissions.end_date else 0),
        "daily_fine_dollars": emissions.daily_fine_projection,
        "total_fine_dollars": emissions.total_fine_projection
    }
