"""
Test Suite for LL11 Facade Inspection Tracker

Tests cover:
- FISP cycle status calculations
- Building risk assessments
- SWO predictions
- Critical examination report parsing
- Fine projections

Target: 90%+ coverage
"""
import pytest
from datetime import datetime, timedelta
from packages.core.ll11_facade_inspection_tracker import (
    LL11FacadeInspectionTracker,
    BuildingProfile,
    FISPCycleStatus,
    CriticalExaminationReport,
    FacadeRiskAssessment,
    quick_facade_check,
    FISP_CYCLE_YEARS,
    FISP_MIN_STORIES,
    FISP_LATE_FINE,
    FISP_DAILY_PENALTY,
    RISK_MULTIPLIER_PRE_1950,
    RISK_MULTIPLIER_COASTAL,
    COASTAL_ZIPCODES
)


class TestBuildingProfile:
    """Test building profile model"""
    
    def test_create_building_profile(self):
        """Test creating a building profile"""
        building = BuildingProfile(
            bbl="1012340056",
            building_address="123 Main St, Manhattan",
            borough="Manhattan",
            zipcode="10001",
            stories=15,
            year_built=1920,
            building_class="C",
            is_coastal=False,
            is_pre_1950=True
        )
        
        assert building.bbl == "1012340056"
        assert building.stories == 15
        assert building.year_built == 1920
        assert building.is_pre_1950 is True
        assert building.is_coastal is False
    
    def test_coastal_building(self):
        """Test coastal building identification"""
        building = BuildingProfile(
            bbl="3012340056",
            building_address="100 Waterfront Dr, Brooklyn",
            borough="Brooklyn",
            zipcode="11201",  # Brooklyn waterfront
            stories=10,
            year_built=1980,
            building_class="C"
        )
        
        # Check if zipcode is in coastal zones
        assert building.zipcode in COASTAL_ZIPCODES


class TestFISPCycleStatus:
    """Test FISP cycle status calculations"""
    
    def test_calculate_compliant_status(self):
        """Test compliant building (filed on time)"""
        tracker = LL11FacadeInspectionTracker()
        
        cycle_start = datetime.now() - timedelta(days=365 * 3)  # 3 years ago
        last_filing = datetime.now() - timedelta(days=30)  # Filed recently
        
        status = tracker.calculate_cycle_status(
            bbl="1012340056",
            cycle_number=9,
            cycle_start_date=cycle_start,
            last_filing_date=last_filing,
            current_rating="SAFE"
        )
        
        assert isinstance(status, FISPCycleStatus)
        assert status.status == "COMPLIANT"
        assert status.days_overdue == 0
        assert status.projected_fine == 0.0
        assert status.swo_probability < 0.5
    
    def test_calculate_warning_status(self):
        """Test warning status (approaching deadline)"""
        tracker = LL11FacadeInspectionTracker()
        
        # Cycle started 4.8 years ago (60 days until deadline)
        cycle_start = datetime.now() - timedelta(days=365 * 4 + 305)
        
        status = tracker.calculate_cycle_status(
            bbl="1012340056",
            cycle_number=9,
            cycle_start_date=cycle_start,
            last_filing_date=None,
            current_rating="SAFE"
        )
        
        assert status.status == "WARNING"
        assert 0 < status.days_until_deadline <= 90
        assert status.days_overdue == 0
    
    def test_calculate_overdue_status(self):
        """Test overdue status with fines"""
        tracker = LL11FacadeInspectionTracker()
        
        # Cycle started 6 years ago (1 year overdue)
        cycle_start = datetime.now() - timedelta(days=365 * 6)
        
        status = tracker.calculate_cycle_status(
            bbl="1012340056",
            cycle_number=9,
            cycle_start_date=cycle_start,
            last_filing_date=None,
            current_rating=None
        )
        
        assert status.status == "OVERDUE"
        assert status.days_overdue > 0
        assert status.projected_fine > FISP_LATE_FINE
        assert status.daily_penalty_exposure == FISP_DAILY_PENALTY
    
    def test_unsafe_condition_increases_swo_probability(self):
        """Test that unsafe conditions increase SWO probability"""
        tracker = LL11FacadeInspectionTracker()
        
        cycle_start = datetime.now() - timedelta(days=365 * 4)
        
        # Safe condition
        status_safe = tracker.calculate_cycle_status(
            bbl="1012340056",
            cycle_number=9,
            cycle_start_date=cycle_start,
            current_rating="SAFE"
        )
        
        # Unsafe condition
        status_unsafe = tracker.calculate_cycle_status(
            bbl="1012340056",
            cycle_number=9,
            cycle_start_date=cycle_start,
            current_rating="UNSAFE_CRITICAL"
        )
        
        assert status_unsafe.swo_probability > status_safe.swo_probability
        assert status_unsafe.requires_immediate_repair is True
        assert status_safe.requires_immediate_repair is False


class TestFacadeRiskAssessment:
    """Test comprehensive risk assessment"""
    
    def test_assess_pre_1950_building_risk(self):
        """Test risk assessment for pre-1950 building"""
        tracker = LL11FacadeInspectionTracker()
        
        building = BuildingProfile(
            bbl="1012340056",
            building_address="123 Old Building St",
            borough="Manhattan",
            zipcode="10001",
            stories=12,
            year_built=1920,
            building_class="C",
            is_coastal=False,
            is_pre_1950=True
        )
        
        cycle_start = datetime.now() - timedelta(days=365 * 4)
        cycle_status = tracker.calculate_cycle_status(
            bbl=building.bbl,
            cycle_number=9,
            cycle_start_date=cycle_start,
            current_rating="SAFE_WITH_REPAIR"
        )
        
        assessment = tracker.assess_building_risk(building, cycle_status)
        
        assert isinstance(assessment, FacadeRiskAssessment)
        assert assessment.age_risk_factor == RISK_MULTIPLIER_PRE_1950
        assert assessment.composite_risk_score > 1.0
        assert len(assessment.recommended_actions) > 0
    
    def test_assess_coastal_building_risk(self):
        """Test risk assessment for coastal building"""
        tracker = LL11FacadeInspectionTracker()
        
        building = BuildingProfile(
            bbl="3012340056",
            building_address="100 Waterfront Dr",
            borough="Brooklyn",
            zipcode="11201",  # Coastal
            stories=10,
            year_built=1980,
            building_class="C",
            is_coastal=True,
            is_pre_1950=False
        )
        
        cycle_start = datetime.now() - timedelta(days=365 * 3)
        cycle_status = tracker.calculate_cycle_status(
            bbl=building.bbl,
            cycle_number=9,
            cycle_start_date=cycle_start,
            current_rating="SAFE"
        )
        
        assessment = tracker.assess_building_risk(building, cycle_status)
        
        assert assessment.coastal_risk_factor == RISK_MULTIPLIER_COASTAL
        assert assessment.composite_risk_score >= RISK_MULTIPLIER_COASTAL
    
    def test_assess_critical_unsafe_building(self):
        """Test assessment for critically unsafe building"""
        tracker = LL11FacadeInspectionTracker()
        
        building = BuildingProfile(
            bbl="1012340056",
            building_address="123 Danger St",
            borough="Manhattan",
            zipcode="10001",
            stories=15,
            year_built=1950,
            building_class="C",
            is_coastal=False,
            is_pre_1950=False
        )
        
        cycle_start = datetime.now() - timedelta(days=365 * 5 + 30)  # Overdue
        cycle_status = tracker.calculate_cycle_status(
            bbl=building.bbl,
            cycle_number=9,
            cycle_start_date=cycle_start,
            current_rating="UNSAFE_CRITICAL"
        )
        
        assessment = tracker.assess_building_risk(building, cycle_status)
        
        assert assessment.urgency_level == "CRITICAL"
        assert assessment.swo_prediction is True
        assert assessment.swo_probability > 0.75
        assert assessment.total_fine_exposure > 0
        
        # Should have critical recommendations
        critical_recs = [r for r in assessment.recommended_actions if "CRITICAL" in r or "URGENT" in r]
        assert len(critical_recs) > 0
    
    def test_swo_prediction_threshold(self):
        """Test SWO prediction at threshold"""
        tracker = LL11FacadeInspectionTracker()
        
        building = BuildingProfile(
            bbl="1012340056",
            building_address="123 Test St",
            borough="Manhattan",
            zipcode="10001",
            stories=10,
            year_built=1960,
            building_class="C"
        )
        
        # Create conditions that push SWO probability high
        cycle_start = datetime.now() - timedelta(days=365 * 5 + 100)  # Well overdue
        cycle_status = tracker.calculate_cycle_status(
            bbl=building.bbl,
            cycle_number=9,
            cycle_start_date=cycle_start,
            current_rating="UNSAFE"
        )
        
        assessment = tracker.assess_building_risk(building, cycle_status)
        
        # With overdue + unsafe, should predict SWO
        assert assessment.swo_probability >= 0.75


class TestCriticalExaminationReport:
    """Test CER parsing"""
    
    def test_parse_safe_report(self):
        """Test parsing a safe facade report"""
        tracker = LL11FacadeInspectionTracker()
        
        report_text = """
        Critical Examination Report
        Engineer: John Smith
        License PE #: 123456
        Filing #: 987654321
        
        The facade is structurally sound and safe. No repairs required.
        Facade material is brick in good condition.
        Photos attached showing all elevations.
        """
        
        report = tracker.parse_critical_examination_report(
            report_text=report_text,
            bbl="1012340056",
            report_date=datetime.now()
        )
        
        assert isinstance(report, CriticalExaminationReport)
        assert report.qe_name == "John Smith"
        assert report.qe_license == "123456"
        assert report.filing_number == "987654321"
        assert report.facade_rating == "SAFE"
        assert report.facade_material == "brick"
        assert report.photos_attached is True
        assert report.repair_required_within_days is None
    
    def test_parse_unsafe_report(self):
        """Test parsing an unsafe facade report"""
        tracker = LL11FacadeInspectionTracker()
        
        report_text = """
        Critical Examination Report
        Engineer: Jane Doe
        PE License: 654321
        Filing Number: 123456789
        
        UNSAFE CONDITION IDENTIFIED
        Critical spalling of brick facade on east elevation.
        Significant deterioration requiring immediate repair.
        Stone coping is loose and poses falling hazard.
        
        Critical Items:
        - East facade spalling (floors 8-12)
        - Loose coping at parapet
        - Cracked mortar joints
        
        Repair required within 90 days per DOB requirements.
        """
        
        report = tracker.parse_critical_examination_report(
            report_text=report_text,
            bbl="1012340056",
            report_date=datetime.now()
        )
        
        assert report.facade_rating == "UNSAFE"
        assert report.critical_items_count > 0
        assert report.repair_required_within_days == 90
        assert report.facade_material in ["brick", "stone"]


class TestQuickFacadeCheck:
    """Test convenience function"""
    
    def test_quick_check_compliant_building(self):
        """Test quick check for compliant building"""
        result = quick_facade_check(
            bbl="1012340056",
            building_address="123 Main St, Manhattan",
            stories=10,
            year_built=1980,
            zipcode="10001",
            cycle_start_date=datetime.now() - timedelta(days=365 * 3),
            current_rating="SAFE"
        )
        
        assert result["requires_fisp"] is True
        assert result["compliance_status"] in ["COMPLIANT", "WARNING"]
        assert result["urgency_level"] in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    
    def test_quick_check_building_too_small(self):
        """Test quick check for building below FISP threshold"""
        result = quick_facade_check(
            bbl="1012340056",
            building_address="123 Small St",
            stories=5,  # Below 6-story threshold
            year_built=2000,
            zipcode="10001",
            cycle_start_date=datetime.now()
        )
        
        assert result["requires_fisp"] is False
        assert "reason" in result
    
    def test_quick_check_overdue_building(self):
        """Test quick check for overdue building"""
        result = quick_facade_check(
            bbl="1012340056",
            building_address="123 Overdue St",
            stories=12,
            year_built=1960,
            zipcode="10001",
            cycle_start_date=datetime.now() - timedelta(days=365 * 6),  # 6 years ago
            current_rating=None
        )
        
        assert result["requires_fisp"] is True
        assert result["days_overdue"] > 0
        assert result["total_fine_exposure"] > FISP_LATE_FINE
        assert result["urgency_level"] in ["CRITICAL", "HIGH"]


class TestConstants:
    """Test that constants are properly defined"""
    
    def test_fisp_constants(self):
        """Test FISP constants"""
        assert FISP_CYCLE_YEARS == 5
        assert FISP_MIN_STORIES == 6
        assert FISP_LATE_FINE > 0
        assert FISP_DAILY_PENALTY > 0
    
    def test_risk_multipliers(self):
        """Test risk multipliers"""
        assert RISK_MULTIPLIER_PRE_1950 > 1.0
        assert RISK_MULTIPLIER_COASTAL > 1.0
    
    def test_coastal_zipcodes(self):
        """Test coastal zipcodes are defined"""
        assert isinstance(COASTAL_ZIPCODES, set)
        assert len(COASTAL_ZIPCODES) > 0
        assert "11201" in COASTAL_ZIPCODES  # Brooklyn waterfront
        assert "10004" in COASTAL_ZIPCODES  # Manhattan waterfront


class TestIntegration:
    """Integration tests for complete workflows"""
    
    def test_full_risk_assessment_workflow(self):
        """Test complete risk assessment workflow"""
        tracker = LL11FacadeInspectionTracker()
        
        # Create pre-1950 coastal building (high risk)
        building = BuildingProfile(
            bbl="3012340056",
            building_address="100 Old Waterfront Dr",
            borough="Brooklyn",
            zipcode="11201",
            stories=15,
            year_built=1925,
            building_class="C",
            is_coastal=True,
            is_pre_1950=True
        )
        
        # Overdue cycle with unsafe condition
        cycle_start = datetime.now() - timedelta(days=365 * 5 + 60)
        cycle_status = tracker.calculate_cycle_status(
            bbl=building.bbl,
            cycle_number=9,
            cycle_start_date=cycle_start,
            current_rating="UNSAFE"
        )
        
        # Full assessment
        assessment = tracker.assess_building_risk(building, cycle_status)
        
        # Verify high risk building triggers appropriate responses
        assert assessment.composite_risk_score > 3.0  # Multiple risk factors
        assert assessment.urgency_level in ["CRITICAL", "HIGH"]
        assert assessment.swo_probability > 0.5
        assert assessment.total_fine_exposure > 0
        assert len(assessment.recommended_actions) >= 2
        
        # Check risk factors are applied
        assert assessment.age_risk_factor == RISK_MULTIPLIER_PRE_1950
        assert assessment.coastal_risk_factor == RISK_MULTIPLIER_COASTAL


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
