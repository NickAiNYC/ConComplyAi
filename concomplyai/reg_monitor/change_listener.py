"""Regulatory change listener that tracks sources and detects version changes.

Monitors registered regulatory sources for updates and produces
``RegulatoryUpdate`` records when a new version is detected.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)


class RegulatorySource(BaseModel):
    """Immutable snapshot of a tracked regulatory source."""

    model_config = ConfigDict(frozen=True)

    source_id: str = Field(
        ...,
        description="Unique identifier for the regulatory source.",
    )
    name: str = Field(
        ...,
        description="Human-readable name of the regulatory source.",
    )
    current_version: str = Field(
        ...,
        description="Current known version string of the source.",
    )
    url: str = Field(
        ...,
        description="URL where the regulatory text is published.",
    )
    last_checked: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of the most recent check.",
    )


class RegulatoryUpdate(BaseModel):
    """Immutable record of a detected regulatory change."""

    model_config = ConfigDict(frozen=True)

    update_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for this update record.",
    )
    source_id: str = Field(
        ...,
        description="Identifier of the regulatory source that changed.",
    )
    old_version: str = Field(
        ...,
        description="Previous version string before the update.",
    )
    new_version: str = Field(
        ...,
        description="New version string after the update.",
    )
    detected_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when the change was detected.",
    )
    changes_summary: str = Field(
        ...,
        description="Brief textual summary of the detected changes.",
    )


class RegulatoryChangeListener:
    """Tracks regulatory sources and detects version changes.

    Register sources via ``register_source`` and then call
    ``check_for_updates`` with the latest version and text to detect
    whether the regulation has changed.
    """

    def __init__(self) -> None:
        self._sources: dict[str, RegulatorySource] = {}

    def register_source(
        self,
        source_id: str,
        name: str,
        current_version: str,
        url: str,
    ) -> None:
        """Register a new regulatory source to track.

        Args:
            source_id: Unique identifier for the source.
            name: Human-readable name.
            current_version: The version string currently in effect.
            url: Canonical URL of the regulation.
        """
        source = RegulatorySource(
            source_id=source_id,
            name=name,
            current_version=current_version,
            url=url,
        )
        self._sources[source_id] = source
        logger.info(
            '{"action":"register_source","source_id":"%s","version":"%s"}',
            source_id,
            current_version,
        )

    def check_for_updates(
        self,
        source_id: str,
        new_version: str,
        new_text: str,
    ) -> RegulatoryUpdate | None:
        """Detect whether a regulatory source has changed.

        Compares *new_version* against the stored version.  When a change
        is detected, the internal record is updated and a
        ``RegulatoryUpdate`` is returned.

        Args:
            source_id: Identifier of the previously registered source.
            new_version: Latest version string to compare against.
            new_text: Full text of the new regulation (used in summary).

        Returns:
            A ``RegulatoryUpdate`` if the version changed, otherwise ``None``.

        Raises:
            KeyError: If *source_id* has not been registered.
        """
        source = self._sources.get(source_id)
        if source is None:
            raise KeyError(f"Source '{source_id}' is not registered.")

        if new_version == source.current_version:
            # Update last_checked timestamp even when no change is found.
            self._sources[source_id] = RegulatorySource(
                source_id=source.source_id,
                name=source.name,
                current_version=source.current_version,
                url=source.url,
                last_checked=datetime.now(timezone.utc),
            )
            return None

        old_version = source.current_version
        word_count = len(new_text.split())
        summary = (
            f"Regulation '{source.name}' updated from {old_version} to "
            f"{new_version}. New text contains {word_count} words."
        )

        update = RegulatoryUpdate(
            source_id=source_id,
            old_version=old_version,
            new_version=new_version,
            changes_summary=summary,
        )

        # Replace source record with updated version.
        self._sources[source_id] = RegulatorySource(
            source_id=source.source_id,
            name=source.name,
            current_version=new_version,
            url=source.url,
            last_checked=datetime.now(timezone.utc),
        )

        logger.info(
            '{"action":"update_detected","source_id":"%s","old":"%s","new":"%s"}',
            source_id,
            old_version,
            new_version,
        )
        return update

    def get_tracked_sources(self) -> list[RegulatorySource]:
        """Return a list of all currently tracked regulatory sources.

        Returns:
            Snapshot list of ``RegulatorySource`` instances.
        """
        return list(self._sources.values())
