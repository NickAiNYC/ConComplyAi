"""Diff engine for comparing old and new regulation text.

Uses Python's ``difflib`` to produce structured diffs with a severity
classification based on the proportion of changed content.
"""

from __future__ import annotations

import difflib
import logging
import uuid
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)


class RegulationDiff(BaseModel):
    """Immutable result of comparing two regulation text versions."""

    model_config = ConfigDict(frozen=True)

    diff_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for this diff result.",
    )
    added_lines: list[str] = Field(
        default_factory=list,
        description="Lines present in the new text but absent from the old.",
    )
    removed_lines: list[str] = Field(
        default_factory=list,
        description="Lines present in the old text but absent from the new.",
    )
    modified_sections: list[str] = Field(
        default_factory=list,
        description="Section headers or context lines surrounding modifications.",
    )
    change_severity: Literal["MINOR", "MODERATE", "MAJOR", "BREAKING"] = Field(
        ...,
        description="Severity classification derived from change proportion.",
    )
    computed_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when the diff was computed.",
    )


class RegulationDiffEngine:
    """Compares two regulation texts and produces a structured diff.

    Severity thresholds (proportion of total lines affected):
        * ≤ 5 %  → MINOR
        * ≤ 20 % → MODERATE
        * ≤ 50 % → MAJOR
        * > 50 % → BREAKING
    """

    @staticmethod
    def _classify_severity(
        changed_count: int,
        total_lines: int,
    ) -> Literal["MINOR", "MODERATE", "MAJOR", "BREAKING"]:
        """Return a severity label based on changed-line ratio.

        Args:
            changed_count: Number of added + removed lines.
            total_lines: Max of old/new line counts (baseline).

        Returns:
            One of the four severity literals.
        """
        if total_lines == 0:
            return "MINOR"
        ratio = changed_count / total_lines
        if ratio > 0.50:
            return "BREAKING"
        if ratio > 0.20:
            return "MAJOR"
        if ratio > 0.05:
            return "MODERATE"
        return "MINOR"

    def compute_diff(self, old_text: str, new_text: str) -> RegulationDiff:
        """Compare *old_text* and *new_text* and return a ``RegulationDiff``.

        Args:
            old_text: The previous regulation text.
            new_text: The updated regulation text.

        Returns:
            A ``RegulationDiff`` containing added/removed lines, modified
            section markers, and a severity classification.
        """
        old_lines = old_text.splitlines(keepends=False)
        new_lines = new_text.splitlines(keepends=False)

        differ = difflib.unified_diff(
            old_lines,
            new_lines,
            lineterm="",
            n=1,
        )

        added: list[str] = []
        removed: list[str] = []
        modified_sections: list[str] = []

        for line in differ:
            if line.startswith("@@"):
                modified_sections.append(line.strip())
            elif line.startswith("+") and not line.startswith("+++"):
                added.append(line[1:])
            elif line.startswith("-") and not line.startswith("---"):
                removed.append(line[1:])

        total_lines = max(len(old_lines), len(new_lines), 1)
        changed_count = len(added) + len(removed)
        severity = self._classify_severity(changed_count, total_lines)

        diff = RegulationDiff(
            added_lines=added,
            removed_lines=removed,
            modified_sections=modified_sections,
            change_severity=severity,
        )

        logger.info(
            '{"action":"compute_diff","diff_id":"%s","added":%d,"removed":%d,"severity":"%s"}',
            diff.diff_id,
            len(added),
            len(removed),
            severity,
        )
        return diff
