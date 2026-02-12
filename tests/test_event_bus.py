"""Tests for concomplyai.core.event_bus module.

Covers ComplianceEvent model creation, EventBus subscribe/publish,
multiple subscribers, no-subscriber publishing, and subscriber listing.
"""

import re

import pytest
from pydantic import ValidationError

from concomplyai.core.event_bus import ComplianceEvent, EventBus


class TestComplianceEvent:
    """Tests for the ComplianceEvent Pydantic model."""

    def test_create_with_all_fields(self):
        """ComplianceEvent should populate every field correctly."""
        event = ComplianceEvent(
            event_type="guard.validation.completed",
            source="guard_agent",
            payload={"violation_id": "V-001"},
            severity="HIGH",
        )

        assert event.event_type == "guard.validation.completed"
        assert event.source == "guard_agent"
        assert event.payload == {"violation_id": "V-001"}
        assert event.severity == "HIGH"
        assert event.event_id  # auto-generated UUID
        assert event.timestamp is not None

    def test_default_severity_is_low(self):
        """Severity should default to LOW when not provided."""
        event = ComplianceEvent(
            event_type="compliance.check_completed",
            source="test",
        )
        assert event.severity == "LOW"

    def test_default_payload_is_empty_dict(self):
        """Payload should default to an empty dict."""
        event = ComplianceEvent(
            event_type="compliance.check_completed",
            source="test",
        )
        assert event.payload == {}

    def test_event_id_is_uuid(self):
        """Auto-generated event_id should be a valid UUID string."""
        event = ComplianceEvent(
            event_type="compliance.alert",
            source="test",
        )
        uuid_pattern = re.compile(
            r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
        )
        assert uuid_pattern.match(event.event_id)

    def test_event_is_frozen(self):
        """ComplianceEvent should be immutable (frozen)."""
        event = ComplianceEvent(
            event_type="compliance.violation",
            source="test",
        )
        with pytest.raises(ValidationError):
            event.severity = "CRITICAL"

    def test_invalid_severity_raises(self):
        """An invalid severity literal should raise ValidationError."""
        with pytest.raises(ValidationError):
            ComplianceEvent(
                event_type="compliance.violation",
                source="test",
                severity="UNKNOWN",
            )


class TestEventBus:
    """Tests for the EventBus subscribe/publish dispatcher."""

    @pytest.fixture
    def bus(self):
        return EventBus()

    def test_subscribe_and_publish(self, bus):
        """A subscribed handler should receive the published event."""
        received = []
        bus.subscribe("compliance.violation", lambda e: received.append(e))

        event = ComplianceEvent(
            event_type="compliance.violation",
            source="test",
        )
        bus.publish(event)

        assert len(received) == 1
        assert received[0].event_id == event.event_id

    def test_multiple_subscribers_same_type(self, bus):
        """All handlers for the same event type should be invoked."""
        results_a = []
        results_b = []
        bus.subscribe("compliance.alert", lambda e: results_a.append(e))
        bus.subscribe("compliance.alert", lambda e: results_b.append(e))

        event = ComplianceEvent(
            event_type="compliance.alert",
            source="test",
        )
        bus.publish(event)

        assert len(results_a) == 1
        assert len(results_b) == 1

    def test_publish_with_no_subscribers(self, bus):
        """Publishing to an event type with no subscribers should not raise."""
        event = ComplianceEvent(
            event_type="nonexistent.event",
            source="test",
        )
        bus.publish(event)  # should not raise

    def test_get_subscribers_returns_copy(self, bus):
        """get_subscribers should return a list copy of registered handlers."""
        handler = lambda e: None  # noqa: E731
        bus.subscribe("compliance.violation", handler)

        subscribers = bus.get_subscribers("compliance.violation")
        assert len(subscribers) == 1
        assert subscribers[0] is handler

    def test_get_subscribers_empty_for_unknown_type(self, bus):
        """Querying subscribers for an unregistered type returns empty list."""
        assert bus.get_subscribers("unknown.type") == []

    def test_handler_error_does_not_block_others(self, bus):
        """A failing handler must not prevent subsequent handlers from running."""
        results = []

        def bad_handler(event):
            raise RuntimeError("boom")

        bus.subscribe("compliance.alert", bad_handler)
        bus.subscribe("compliance.alert", lambda e: results.append("ok"))

        event = ComplianceEvent(
            event_type="compliance.alert",
            source="test",
        )
        bus.publish(event)

        assert results == ["ok"]
