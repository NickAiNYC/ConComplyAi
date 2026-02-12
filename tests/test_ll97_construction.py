"""
Test Suite for LL97 Construction Engine

Tests cover:
- Equipment emissions calculations
- Site emissions totals
- Phase-based emissions
- Fine projections
- Mitigation recommendations

Target: 90%+ coverage
"""
import pytest
from datetime import datetime, timedelta
from packages.core.ll97_construction_engine import (
    LL97ConstructionEngine,
    EquipmentEmissions,
    ConstructionSiteEmissions,
    MitigationRecommendation,
    calculate_crane_daily_cost,
    estimate_project_carbon_cost,
    EQUIPMENT_FUEL_RATES,
    EMISSIONS_FACTORS,
    CONSTRUCTION_PHASES,
    LL97_FINE_PER_TON_CO2E
)


class TestEquipmentEmissions:
    """Test equipment emissions calculations"""
    
    def test_calculate_diesel_equipment_emissions(self):
        """Test diesel equipment emissions"""
        engine = LL97ConstructionEngine()
        emissions = engine.calculate_equipment_emissions(
            equipment_type="tower_crane",
            hours_operated=10.0,
            fuel_type="diesel"
        )
        
        assert isinstance(emissions, EquipmentEmissions)
        assert emissions.equipment_type == "tower_crane"
        assert emissions.fuel_type == "diesel"
        assert emissions.hours_operated == 10.0
        assert emissions.fuel_consumed_gallons > 0
        assert emissions.co2e_kg > 0
        assert emissions.co2e_tons == emissions.co2e_kg / 1000.0
        
        # Verify calculation: 10 hrs * 12 gal/hr * 10.21 kg/gal
        expected_fuel = 10.0 * EQUIPMENT_FUEL_RATES["tower_crane"]
        expected_co2e = expected_fuel * EMISSIONS_FACTORS["diesel"]
        assert abs(emissions.co2e_kg - expected_co2e) < 0.01
    
    def test_calculate_electric_equipment_emissions(self):
        """Test electric equipment emissions (lower than diesel)"""
        engine = LL97ConstructionEngine()
        emissions = engine.calculate_equipment_emissions(
            equipment_type="tower_crane",
            hours_operated=10.0,
            fuel_type="grid_electricity"
        )
        
        assert emissions.fuel_type == "grid_electricity"
        assert emissions.electricity_consumed_kwh > 0
        assert emissions.fuel_consumed_gallons is None
        assert emissions.co2e_kg > 0
    
    def test_different_equipment_types(self):
        """Test various equipment types"""
        engine = LL97ConstructionEngine()
        
        equipment_types = ["excavator_large", "bulldozer", "concrete_pump", "generator_large"]
        
        for equip_type in equipment_types:
            emissions = engine.calculate_equipment_emissions(
                equipment_type=equip_type,
                hours_operated=8.0
            )
            assert emissions.equipment_type == equip_type
            assert emissions.co2e_kg > 0


class TestConstructionSiteEmissions:
    """Test complete site emissions calculations"""
    
    def test_calculate_site_emissions(self):
        """Test site emissions calculation"""
        engine = LL97ConstructionEngine()
        
        equipment_usage = {
            "tower_crane": 10.0,
            "excavator_large": 8.0,
            "generator_large": 12.0
        }
        
        site_emissions = engine.calculate_site_emissions(
            site_id="TEST-001",
            permit_number="BLD-2024-12345",
            site_address="123 Main St, Manhattan",
            project_phase="structural",
            start_date=datetime.now(),
            equipment_usage=equipment_usage,
            temporary_power_kwh=100.0
        )
        
        assert isinstance(site_emissions, ConstructionSiteEmissions)
        assert site_emissions.site_id == "TEST-001"
        assert site_emissions.permit_number == "BLD-2024-12345"
        assert len(site_emissions.equipment_emissions) == 3
        assert site_emissions.total_co2e_kg > 0
        assert site_emissions.total_co2e_tons == site_emissions.total_co2e_kg / 1000.0
        assert site_emissions.daily_fine_projection >= 0
    
    def test_site_emissions_with_limit(self):
        """Test site emissions with emissions limit"""
        engine = LL97ConstructionEngine(emissions_limit_tons=1.0)
        
        equipment_usage = {
            "tower_crane": 10.0,
            "excavator_large": 8.0
        }
        
        site_emissions = engine.calculate_site_emissions(
            site_id="TEST-002",
            permit_number="BLD-2024-67890",
            site_address="456 Broadway, Brooklyn",
            project_phase="foundation",
            start_date=datetime.now(),
            equipment_usage=equipment_usage,
            end_date=datetime.now() + timedelta(days=45)
        )
        
        # Check if fine projection is calculated based on excess
        if site_emissions.over_limit:
            assert site_emissions.daily_fine_projection > 0
            excess_tons = site_emissions.total_co2e_tons - 1.0
            expected_daily_fine = excess_tons * LL97_FINE_PER_TON_CO2E
            assert abs(site_emissions.daily_fine_projection - expected_daily_fine) < 0.01
    
    def test_calculate_phase_emissions(self):
        """Test standard phase emissions calculation"""
        engine = LL97ConstructionEngine()
        
        for phase_name in CONSTRUCTION_PHASES.keys():
            emissions = engine.calculate_phase_emissions(
                site_id=f"TEST-{phase_name}",
                permit_number=f"BLD-2024-{phase_name}",
                site_address="Test Address",
                project_phase=phase_name,
                start_date=datetime.now()
            )
            
            assert emissions.project_phase == phase_name
            assert emissions.end_date is not None
            assert emissions.total_co2e_kg > 0
            
            # Verify duration matches phase template
            phase_info = CONSTRUCTION_PHASES[phase_name]
            expected_duration = phase_info["duration_days"]
            actual_duration = (emissions.end_date - emissions.start_date).days
            assert actual_duration == expected_duration


class TestMitigationRecommendations:
    """Test mitigation recommendation generation"""
    
    def test_generate_recommendations_for_cranes(self):
        """Test recommendations for sites with cranes"""
        engine = LL97ConstructionEngine()
        
        site_emissions = engine.calculate_phase_emissions(
            site_id="TEST-CRANES",
            permit_number="BLD-2024-CRANE",
            site_address="Crane Test Site",
            project_phase="structural",
            start_date=datetime.now()
        )
        
        recommendations = engine.generate_mitigation_recommendations(site_emissions)
        
        assert isinstance(recommendations, list)
        assert len(recommendations) > 0
        
        # Should have crane upgrade recommendation
        crane_recs = [r for r in recommendations if "crane" in r.title.lower()]
        assert len(crane_recs) > 0
        
        # Check recommendation structure
        for rec in recommendations:
            assert isinstance(rec, MitigationRecommendation)
            assert rec.title
            assert rec.description
            assert rec.implementation_cost > 0
            assert rec.annual_savings > 0
            assert rec.emissions_reduction_tons > 0
            assert rec.priority in ["HIGH", "MEDIUM", "LOW"]
    
    def test_recommendations_sorted_by_priority(self):
        """Test that recommendations are sorted by priority and payback"""
        engine = LL97ConstructionEngine()
        
        site_emissions = engine.calculate_phase_emissions(
            site_id="TEST-SORT",
            permit_number="BLD-2024-SORT",
            site_address="Sort Test",
            project_phase="foundation",
            start_date=datetime.now()
        )
        
        recommendations = engine.generate_mitigation_recommendations(site_emissions)
        
        # Verify HIGH priority comes before MEDIUM/LOW
        priorities = [r.priority for r in recommendations]
        if "HIGH" in priorities and "MEDIUM" in priorities:
            high_idx = priorities.index("HIGH")
            medium_idx = priorities.index("MEDIUM")
            assert high_idx < medium_idx


class TestConvenienceFunctions:
    """Test convenience functions"""
    
    def test_calculate_crane_daily_cost(self):
        """Test crane daily cost calculation"""
        result = calculate_crane_daily_cost(crane_type="tower_crane", hours_per_day=10.0)
        
        assert isinstance(result, dict)
        assert result["equipment_type"] == "tower_crane"
        assert result["hours_per_day"] == 10.0
        assert result["daily_emissions_kg"] > 0
        assert result["daily_emissions_tons"] > 0
        assert result["daily_fine_dollars"] > 0
        assert result["monthly_fine_dollars"] == result["daily_fine_dollars"] * 30
        assert result["annual_fine_dollars"] == result["daily_fine_dollars"] * 365
    
    def test_estimate_project_carbon_cost(self):
        """Test project carbon cost estimation"""
        result = estimate_project_carbon_cost(
            project_phase="excavation",
            start_date=datetime.now()
        )
        
        assert isinstance(result, dict)
        assert result["project_phase"] == "excavation"
        assert result["duration_days"] > 0
        assert result["daily_emissions_tons"] > 0
        assert result["total_emissions_tons"] > 0
        assert result["daily_fine_dollars"] >= 0
        assert result["total_fine_dollars"] >= 0


class TestConstants:
    """Test that constants are properly defined"""
    
    def test_emissions_factors(self):
        """Test emissions factors are defined"""
        assert "diesel" in EMISSIONS_FACTORS
        assert "gasoline" in EMISSIONS_FACTORS
        assert "grid_electricity" in EMISSIONS_FACTORS
        assert all(v > 0 for v in EMISSIONS_FACTORS.values())
    
    def test_equipment_fuel_rates(self):
        """Test equipment fuel rates are defined"""
        assert "tower_crane" in EQUIPMENT_FUEL_RATES
        assert "excavator_large" in EQUIPMENT_FUEL_RATES
        assert "generator_large" in EQUIPMENT_FUEL_RATES
        assert all(v > 0 for v in EQUIPMENT_FUEL_RATES.values())
    
    def test_construction_phases(self):
        """Test construction phases are defined"""
        required_phases = ["excavation", "foundation", "structural", "facade", "interior"]
        for phase in required_phases:
            assert phase in CONSTRUCTION_PHASES
            assert "duration_days" in CONSTRUCTION_PHASES[phase]
            assert "equipment" in CONSTRUCTION_PHASES[phase]
    
    def test_ll97_fine_rate(self):
        """Test LL97 fine rate is correct"""
        assert LL97_FINE_PER_TON_CO2E == 268.0


class TestIntegration:
    """Integration tests for complete workflows"""
    
    def test_full_excavation_workflow(self):
        """Test complete excavation phase workflow"""
        engine = LL97ConstructionEngine(emissions_limit_tons=5.0)
        
        # Calculate emissions
        emissions = engine.calculate_phase_emissions(
            site_id="INT-001",
            permit_number="BLD-2024-INT001",
            site_address="123 Integration St",
            project_phase="excavation",
            start_date=datetime.now()
        )
        
        # Generate recommendations
        recommendations = engine.generate_mitigation_recommendations(emissions)
        
        # Verify complete workflow
        assert emissions.total_co2e_tons > 0
        assert len(recommendations) > 0
        
        # Check that recommendations address equipment used
        equipment_types = [e.equipment_type for e in emissions.equipment_emissions]
        rec_equipment = []
        for rec in recommendations:
            rec_equipment.extend(rec.equipment_affected)
        
        # At least some overlap between equipment and recommendations
        assert any(equip in rec_equipment for equip in equipment_types)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
