"""Real-time compliance monitoring agent.

Subscribes to all ``compliance.*`` events via wildcard registration and
tracks metrics, generating :class:`MonitoringAlert` instances when
configurable thresholds are breached.
"""

from __future__ import annotations

import logging
import time
import uuid
from collections import defaultdict
from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field

from concomplyai.core.event_bus import ComplianceEvent, EventBus

logger = logging.getLogger(__name__)

_CRITICAL_ALERT_THRESHOLD = 5
_CRITICAL_WINDOW_SECONDS = 3600.0


class MonitoringAlert(BaseModel):
    """Immutable alert raised when monitoring thresholds are exceeded."""

    model_config = ConfigDict(frozen=True)

    alert_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for this alert.",
    )
    alert_type: str = Field(
        ...,
        description="Category of alert, e.g. 'critical_threshold_exceeded'.",
    )
    message: str = Field(
        ...,
        description="Human-readable alert message.",
    )
    severity: str = Field(
        ...,
        description="Alert severity level.",
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when the alert was generated.",
    )
    related_events: list[str] = Field(
        default_factory=list,
        description="Event IDs that contributed to this alert.",
    )


class MonitoringMetrics(BaseModel):
    """Snapshot of current monitoring statistics."""

    model_config = ConfigDict(frozen=True)

    total_events: int = Field(
        default=0,
        ge=0,
        description="Total events processed since agent start.",
    )
    events_by_type: dict[str, int] = Field(
        default_factory=dict,
        description="Event counts keyed by event_type.",
    )
    events_by_severity: dict[str, int] = Field(
        default_factory=dict,
        description="Event counts keyed by severity level.",
    )
    alert_count: int = Field(
        default=0,
        ge=0,
        description="Total alerts generated since agent start.",
    )
    uptime_seconds: float = Field(
        default=0.0,
        ge=0.0,
        description="Seconds elapsed since agent initialisation.",
    )


class MonitoringAgent:
    """Tracks all compliance events and raises alerts on threshold breaches.

    The agent subscribes to known ``compliance.*`` event types on the
    provided :class:`EventBus`.  It maintains running counts by type and
    severity and generates a :class:`MonitoringAlert` when the number of
    ``CRITICAL`` events within a rolling one-hour window exceeds the
    configured threshold.
    """

    _WATCHED_EVENT_TYPES: list[str] = [
        "compliance.violation",
        "compliance.report_request",
        "compliance.check_completed",
        "compliance.remediation_applied",
        "compliance.alert",
    ]

    def __init__(self, event_bus: EventBus) -> None:
        self._event_bus = event_bus
        self._start_time = time.monotonic()
        self._total_events = 0
        self._events_by_type: dict[str, int] = defaultdict(int)
        self._events_by_severity: dict[str, int] = defaultdict(int)
        self._alerts: list[MonitoringAlert] = []
        self._critical_timestamps: list[float] = []

        for event_type in self._WATCHED_EVENT_TYPES:
            self._event_bus.subscribe(event_type, self.process_event)

        logger.info('{"agent":"MonitoringAgent","action":"initialized"}')

    def process_event(self, event: ComplianceEvent) -> MonitoringAlert | None:
        """Record *event* metrics and return an alert if thresholds are met.

        Args:
            event: Any compliance event flowing through the bus.

        Returns:
            A :class:`MonitoringAlert` if a threshold was breached,
            otherwise ``None``.
        """
        self._total_events += 1
        self._events_by_type[event.event_type] += 1
        self._events_by_severity[event.severity] += 1

        logger.info(
            '{"agent":"MonitoringAgent","action":"event_processed",'
            '"event_type":"%s","severity":"%s","total_events":%d}',
            event.event_type,
            event.severity,
            self._total_events,
        )

        if event.severity == "CRITICAL":
            return self._evaluate_critical_threshold(event)

        return None

    def get_metrics(self) -> MonitoringMetrics:
        """Return a snapshot of current monitoring metrics.

        Returns:
            An immutable :class:`MonitoringMetrics` instance.
        """
        return MonitoringMetrics(
            total_events=self._total_events,
            events_by_type=dict(self._events_by_type),
            events_by_severity=dict(self._events_by_severity),
            alert_count=len(self._alerts),
            uptime_seconds=time.monotonic() - self._start_time,
        )

    def _evaluate_critical_threshold(
        self, event: ComplianceEvent,
    ) -> MonitoringAlert | None:
        """Check whether the critical-event rate warrants an alert."""
        now = time.monotonic()
        self._critical_timestamps.append(now)

        # Prune timestamps outside the rolling window.
        cutoff = now - _CRITICAL_WINDOW_SECONDS
        self._critical_timestamps = [
            ts for ts in self._critical_timestamps if ts >= cutoff
        ]

        if len(self._critical_timestamps) >= _CRITICAL_ALERT_THRESHOLD:
            recent_ids = [event.event_id]
            alert = MonitoringAlert(
                alert_type="critical_threshold_exceeded",
                message=(
                    f"{len(self._critical_timestamps)} critical events "
                    f"detected within the last "
                    f"{_CRITICAL_WINDOW_SECONDS / 60:.0f} minutes, "
                    f"exceeding threshold of {_CRITICAL_ALERT_THRESHOLD}."
                ),
                severity="CRITICAL",
                related_events=recent_ids,
            )

            self._alerts.append(alert)

            logger.warning(
                '{"agent":"MonitoringAgent","action":"alert_raised",'
                '"alert_type":"critical_threshold_exceeded",'
                '"critical_count":%d,"alert_id":"%s"}',
                len(self._critical_timestamps),
                alert.alert_id,
            )

            return alert

        return None
