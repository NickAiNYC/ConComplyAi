"""Synchronous publish/subscribe event bus for inter-agent communication.

Provides a ``ComplianceEvent`` model and an ``EventBus`` that routes events
to registered handlers by event type.  All dispatching is synchronous so
callers can rely on handler completion before proceeding.
"""

from __future__ import annotations

import logging
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Callable, Literal

from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)


class ComplianceEvent(BaseModel):
    """Immutable record of a compliance-related event flowing through the bus."""

    model_config = ConfigDict(frozen=True)

    event_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for this event instance.",
    )
    event_type: str = Field(
        ...,
        description="Dot-namespaced event type, e.g. 'guard.validation.completed'.",
    )
    source: str = Field(
        ...,
        description="Agent or service that emitted the event.",
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of event creation.",
    )
    payload: dict[str, Any] = Field(
        default_factory=dict,
        description="Arbitrary event data.",
    )
    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] = Field(
        default="LOW",
        description="Severity classification for alerting and prioritisation.",
    )


EventHandler = Callable[[ComplianceEvent], None]


class EventBus:
    """Synchronous, in-process event dispatcher.

    Handlers are invoked in registration order.  A failing handler is
    logged but does **not** prevent subsequent handlers from executing.
    """

    def __init__(self) -> None:
        self._subscribers: dict[str, list[EventHandler]] = defaultdict(list)

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        """Register *handler* to be called for every event of *event_type*.

        Args:
            event_type: The event type string to listen for.
            handler: Callable accepting a single ``ComplianceEvent`` argument.
        """
        self._subscribers[event_type].append(handler)
        logger.info(
            '{"action":"subscribe","event_type":"%s","handler":"%s"}',
            event_type,
            getattr(handler, "__name__", repr(handler)),
        )

    def publish(self, event: ComplianceEvent) -> None:
        """Dispatch *event* to all subscribers of its ``event_type``.

        Each handler is called synchronously.  Exceptions are caught and
        logged so that one broken handler cannot block the rest.

        Args:
            event: The compliance event to broadcast.
        """
        handlers = self._subscribers.get(event.event_type, [])
        logger.info(
            '{"action":"publish","event_type":"%s","event_id":"%s","handler_count":%d}',
            event.event_type,
            event.event_id,
            len(handlers),
        )
        for handler in handlers:
            try:
                handler(event)
            except Exception:
                logger.exception(
                    '{"action":"handler_error","event_type":"%s","handler":"%s"}',
                    event.event_type,
                    getattr(handler, "__name__", repr(handler)),
                )

    def get_subscribers(self, event_type: str) -> list[EventHandler]:
        """Return a copy of the handler list for *event_type*.

        Args:
            event_type: The event type to query.

        Returns:
            List of currently registered handlers (may be empty).
        """
        return list(self._subscribers.get(event_type, []))
