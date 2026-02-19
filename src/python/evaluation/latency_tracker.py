"""
Latency tracking for pipeline evaluation.

Provides a context manager and utilities for measuring execution time
across pipeline phases and end-to-end workflows.
"""

from __future__ import annotations

import time
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any

from src.python.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class TimingRecord:
    """A single timing measurement."""

    name: str
    started_at: float = 0.0
    completed_at: float = 0.0

    @property
    def duration_seconds(self) -> float:
        return self.completed_at - self.started_at


@dataclass
class LatencyReport:
    """Aggregated latency report for an evaluation run."""

    records: list[TimingRecord] = field(default_factory=list)
    target_seconds: float = 30.0

    def add(self, record: TimingRecord) -> None:
        """Add a timing record."""
        self.records.append(record)

    @property
    def total_records(self) -> int:
        return len(self.records)

    @property
    def durations(self) -> list[float]:
        return [r.duration_seconds for r in self.records]

    @property
    def mean_seconds(self) -> float:
        if not self.durations:
            return 0.0
        return sum(self.durations) / len(self.durations)

    @property
    def median_seconds(self) -> float:
        if not self.durations:
            return 0.0
        sorted_d = sorted(self.durations)
        n = len(sorted_d)
        mid = n // 2
        if n % 2 == 0:
            return (sorted_d[mid - 1] + sorted_d[mid]) / 2
        return sorted_d[mid]

    @property
    def p90_seconds(self) -> float:
        """90th percentile latency."""
        if not self.durations:
            return 0.0
        sorted_d = sorted(self.durations)
        idx = int(len(sorted_d) * 0.9)
        idx = min(idx, len(sorted_d) - 1)
        return sorted_d[idx]

    @property
    def min_seconds(self) -> float:
        return min(self.durations) if self.durations else 0.0

    @property
    def max_seconds(self) -> float:
        return max(self.durations) if self.durations else 0.0

    @property
    def within_target_count(self) -> int:
        return sum(1 for d in self.durations if d <= self.target_seconds)

    @property
    def within_target_rate(self) -> float:
        if not self.durations:
            return 0.0
        return self.within_target_count / len(self.durations)

    @property
    def meets_target(self) -> bool:
        """Target: p90 latency <= target_seconds."""
        return self.p90_seconds <= self.target_seconds

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_records": self.total_records,
            "target_seconds": self.target_seconds,
            "mean_seconds": round(self.mean_seconds, 3),
            "median_seconds": round(self.median_seconds, 3),
            "p90_seconds": round(self.p90_seconds, 3),
            "min_seconds": round(self.min_seconds, 3),
            "max_seconds": round(self.max_seconds, 3),
            "within_target_rate": round(self.within_target_rate, 3),
            "meets_target": self.meets_target,
        }


@contextmanager
def track_latency(
    name: str, report: LatencyReport | None = None
) -> Generator[TimingRecord, None, None]:
    """
    Context manager for tracking execution latency.

    Args:
        name: Label for the timing measurement
        report: Optional LatencyReport to automatically add the record to

    Yields:
        TimingRecord with timing data populated on exit
    """
    record = TimingRecord(name=name)
    record.started_at = time.monotonic()

    try:
        yield record
    finally:
        record.completed_at = time.monotonic()

        logger.info(
            "latency_measured",
            name=name,
            duration_seconds=round(record.duration_seconds, 3),
        )

        if report is not None:
            report.add(record)
