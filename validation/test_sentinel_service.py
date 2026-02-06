"""
Tests for SentinelService - Real-time monitoring
Tests the integration of Sentinel-Scope monitoring into ConComplyAi
"""
import pytest
from datetime import datetime, timedelta
from pathlib import Path
import tempfile
import os

from core.services import SentinelService
from core.services.sentinel_service import (
    WatchConfig,
    MonitoringEvent,
    MonitoringEventType
)


class TestSentinelServiceInitialization:
    """Test SentinelService initialization and configuration"""
    
    def test_default_initialization(self):
        """Test service initializes with default config"""
        service = SentinelService()
        
        assert service.watch_config is not None
        assert service.monitoring_events == []
        assert service.is_monitoring is False
        assert service._callbacks == []
    
    def test_custom_config_initialization(self):
        """Test service initializes with custom config"""
        config = WatchConfig(
            watch_paths=['/test/path'],
            file_patterns=['*.pdf'],
            poll_interval_seconds=10,
            auto_trigger_extraction=False
        )
        service = SentinelService(watch_config=config)
        
        assert service.watch_config.watch_paths == ['/test/path']
        assert service.watch_config.file_patterns == ['*.pdf']
        assert service.watch_config.poll_interval_seconds == 10
        assert service.watch_config.auto_trigger_extraction is False


class TestExpirationTracking:
    """Test expiration tracking and warnings"""
    
    def test_add_expiring_item(self):
        """Test adding item to expiration tracking"""
        service = SentinelService()
        exp_date = datetime.now() + timedelta(days=20)
        
        service.add_expiring_item(
            item_id='COI-001',
            item_type='Certificate of Insurance',
            expiration_date=exp_date,
            metadata={'contractor': 'ABC Corp'}
        )
        
        assert len(service._expiring_items) == 1
        assert service._expiring_items[0]['item_id'] == 'COI-001'
    
    def test_expiration_warning_within_30_days(self):
        """Test warning generated for items expiring within 30 days"""
        service = SentinelService()
        exp_date = datetime.now() + timedelta(days=25)
        
        service.add_expiring_item(
            item_id='COI-001',
            item_type='COI',
            expiration_date=exp_date
        )
        
        warnings = service.check_expirations()
        
        assert len(warnings) == 1
        assert warnings[0].event_type == MonitoringEventType.EXPIRATION_WARNING
        # Allow for rounding in days calculation (24 or 25 is acceptable)
        assert warnings[0].data['days_until_expiration'] in [24, 25]
    
    def test_critical_priority_for_7_days_or_less(self):
        """Test critical priority for items expiring in 7 days or less"""
        service = SentinelService()
        exp_date = datetime.now() + timedelta(days=5)
        
        service.add_expiring_item(
            item_id='LIC-001',
            item_type='License',
            expiration_date=exp_date
        )
        
        warnings = service.check_expirations()
        
        assert len(warnings) == 1
        assert warnings[0].priority == 1  # Critical
    
    def test_no_warning_beyond_30_days(self):
        """Test no warning for items expiring beyond 30 days"""
        service = SentinelService()
        exp_date = datetime.now() + timedelta(days=45)
        
        service.add_expiring_item(
            item_id='COI-002',
            item_type='COI',
            expiration_date=exp_date
        )
        
        warnings = service.check_expirations()
        
        assert len(warnings) == 0


class TestDirectoryWatching:
    """Test file system watching capabilities"""
    
    def test_watch_directory_detects_pdf(self):
        """Test detecting PDF files in directory"""
        service = SentinelService()
        
        # Create temp directory with test file
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test_document.pdf"
            test_file.touch()
            
            events = service.watch_directory(tmpdir)
            
            assert len(events) == 1
            assert events[0].event_type == MonitoringEventType.DOCUMENT_DETECTED
            assert 'test_document.pdf' in events[0].source
    
    def test_watch_directory_multiple_files(self):
        """Test detecting multiple files"""
        service = SentinelService()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "doc1.pdf").touch()
            (Path(tmpdir) / "doc2.jpg").touch()
            (Path(tmpdir) / "doc3.png").touch()
            
            events = service.watch_directory(tmpdir)
            
            assert len(events) == 3
    
    def test_watch_directory_ignores_duplicates(self):
        """Test that already-detected files are not reported again"""
        service = SentinelService()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.pdf"
            test_file.touch()
            
            # First scan
            events1 = service.watch_directory(tmpdir)
            assert len(events1) == 1
            
            # Second scan - should not detect again
            events2 = service.watch_directory(tmpdir)
            assert len(events2) == 0
    
    def test_watch_nonexistent_directory(self):
        """Test watching non-existent directory returns empty"""
        service = SentinelService()
        events = service.watch_directory('/nonexistent/path')
        
        assert len(events) == 0


class TestEventManagement:
    """Test event creation, retrieval, and processing"""
    
    def test_report_compliance_event(self):
        """Test reporting compliance violation"""
        service = SentinelService()
        
        event = service.report_compliance_event(
            site_id='SITE-001',
            violation_data={
                'type': 'scaffolding',
                'risk_level': 1,
                'description': 'Unstable scaffolding'
            }
        )
        
        assert event.event_type == MonitoringEventType.COMPLIANCE_VIOLATION
        assert event.source == 'SITE-001'
        assert event.priority == 1
    
    def test_get_live_feed_returns_recent_events(self):
        """Test retrieving live feed of events"""
        service = SentinelService()
        
        # Create multiple events
        for i in range(5):
            service.report_compliance_event(
                site_id=f'SITE-{i}',
                violation_data={'risk_level': 2}
            )
        
        feed = service.get_live_feed(limit=3)
        
        assert len(feed) == 3
        # Should be sorted by timestamp descending (most recent first)
    
    def test_get_live_feed_unprocessed_only(self):
        """Test filtering to unprocessed events only"""
        service = SentinelService()
        
        # Create and process some events
        event1 = service.report_compliance_event('SITE-1', {'risk_level': 2})
        event2 = service.report_compliance_event('SITE-2', {'risk_level': 2})
        
        service.mark_processed(event1.event_id)
        
        feed = service.get_live_feed(unprocessed_only=True)
        
        assert len(feed) == 1
        assert feed[0].event_id == event2.event_id
    
    def test_mark_processed(self):
        """Test marking event as processed"""
        service = SentinelService()
        
        event = service.report_compliance_event('SITE-1', {'risk_level': 2})
        assert event.processed is False
        
        service.mark_processed(event.event_id)
        
        # Re-fetch event from service
        processed_event = next(
            e for e in service.monitoring_events if e.event_id == event.event_id
        )
        assert processed_event.processed is True


class TestStatistics:
    """Test statistics and reporting"""
    
    def test_get_statistics_empty(self):
        """Test statistics with no events"""
        service = SentinelService()
        stats = service.get_statistics()
        
        assert stats['total_events'] == 0
        assert stats['unprocessed_events'] == 0
        assert stats['critical_events'] == 0
        assert stats['monitoring_active'] is False
    
    def test_get_statistics_with_events(self):
        """Test statistics with various events"""
        service = SentinelService()
        
        # Create events with different priorities
        service.report_compliance_event('SITE-1', {'risk_level': 1})  # Critical
        service.report_compliance_event('SITE-2', {'risk_level': 3})
        service.report_compliance_event('SITE-3', {'risk_level': 1})  # Critical
        
        stats = service.get_statistics()
        
        assert stats['total_events'] == 3
        assert stats['unprocessed_events'] == 3
        assert stats['critical_events'] == 2
        assert 'COMPLIANCE_VIOLATION' in stats['events_by_type']


class TestCallbacks:
    """Test callback registration and execution"""
    
    def test_register_callback(self):
        """Test registering event callback"""
        service = SentinelService()
        
        called = []
        
        def callback(event):
            called.append(event.event_id)
        
        service.register_callback(callback)
        
        event = service.report_compliance_event('SITE-1', {'risk_level': 2})
        
        assert len(called) == 1
        assert called[0] == event.event_id
    
    def test_multiple_callbacks(self):
        """Test multiple callbacks are all invoked"""
        service = SentinelService()
        
        call_count = {'count': 0}
        
        def callback1(event):
            call_count['count'] += 1
        
        def callback2(event):
            call_count['count'] += 1
        
        service.register_callback(callback1)
        service.register_callback(callback2)
        
        service.report_compliance_event('SITE-1', {'risk_level': 2})
        
        assert call_count['count'] == 2


class TestUnifiedIngestion:
    """Test unified ingestion triggering"""
    
    def test_trigger_extraction_for_document_event(self):
        """Test triggering extraction for document detection"""
        service = SentinelService()
        
        event = MonitoringEvent(
            event_id='DOC-123',
            event_type=MonitoringEventType.DOCUMENT_DETECTED,
            source='/path/to/doc.pdf',
            data={
                'file_name': 'doc.pdf',
                'file_size': 1024
            }
        )
        
        result = service.trigger_extraction(event)
        
        assert 'document_id' in result
        assert result['file_path'] == '/path/to/doc.pdf'
        assert result['trigger_source'] == 'sentinel_monitoring'
    
    def test_trigger_extraction_wrong_event_type(self):
        """Test error when triggering extraction for non-document event"""
        service = SentinelService()
        
        event = MonitoringEvent(
            event_id='COMP-123',
            event_type=MonitoringEventType.COMPLIANCE_VIOLATION,
            source='SITE-1',
            data={}
        )
        
        result = service.trigger_extraction(event)
        
        assert 'error' in result


class TestIntegration:
    """Integration tests for complete workflows"""
    
    def test_full_document_detection_workflow(self):
        """Test complete workflow: detection -> callback -> extraction"""
        service = SentinelService(
            watch_config=WatchConfig(auto_trigger_extraction=True)
        )
        
        triggered = []
        
        def on_document(event):
            if event.event_type == MonitoringEventType.DOCUMENT_DETECTED:
                extraction_req = service.trigger_extraction(event)
                triggered.append(extraction_req)
        
        service.register_callback(on_document)
        
        # Create test document
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "contract.pdf"
            test_file.touch()
            
            events = service.watch_directory(tmpdir)
            
            assert len(events) == 1
            assert len(triggered) == 1
            assert triggered[0]['file_path'] == str(test_file)
    
    def test_expiration_workflow_with_statistics(self):
        """Test expiration tracking reflected in statistics"""
        service = SentinelService()
        
        # Add expiring items
        service.add_expiring_item(
            'COI-1', 'COI',
            datetime.now() + timedelta(days=15)
        )
        service.add_expiring_item(
            'LIC-1', 'License',
            datetime.now() + timedelta(days=5)
        )
        
        # Check expirations
        warnings = service.check_expirations()
        
        # Get statistics
        stats = service.get_statistics()
        
        assert len(warnings) == 2
        assert stats['total_events'] == 2
        assert stats['critical_events'] == 1  # 5 days = critical
        assert 'EXPIRATION_WARNING' in stats['events_by_type']


# Run tests
if __name__ == '__main__':
    pytest.main([__file__, '-v'])
