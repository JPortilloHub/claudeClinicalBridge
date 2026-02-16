"""
Workflow state management for the clinical pipeline.

Maintains state across agent executions, tracking results from each phase
and timing for latency measurement.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class WorkflowStatus(Enum):
    """Status of a workflow execution."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    NEEDS_REVIEW = "needs_review"


class PhaseStatus(Enum):
    """Status of an individual pipeline phase."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class PhaseResult:
    """Result from a single pipeline phase."""

    phase_name: str
    agent_name: str
    status: PhaseStatus = PhaseStatus.PENDING
    content: str = ""
    error: str | None = None
    usage: dict[str, int] = field(default_factory=dict)
    started_at: float | None = None
    completed_at: float | None = None

    @property
    def duration_seconds(self) -> float | None:
        """Calculate phase duration in seconds."""
        if self.started_at is not None and self.completed_at is not None:
            return self.completed_at - self.started_at
        return None

    def mark_running(self) -> None:
        """Mark phase as running."""
        self.status = PhaseStatus.RUNNING
        self.started_at = time.monotonic()

    def mark_completed(self, content: str, usage: dict[str, int]) -> None:
        """Mark phase as completed with results."""
        self.status = PhaseStatus.COMPLETED
        self.content = content
        self.usage = usage
        self.completed_at = time.monotonic()

    def mark_failed(self, error: str) -> None:
        """Mark phase as failed with error."""
        self.status = PhaseStatus.FAILED
        self.error = error
        self.completed_at = time.monotonic()

    def mark_skipped(self) -> None:
        """Mark phase as skipped."""
        self.status = PhaseStatus.SKIPPED
        self.completed_at = time.monotonic()


@dataclass
class WorkflowState:
    """
    Maintains state across the clinical pipeline execution.

    Tracks the raw note input, results from each agent phase,
    and timing for latency measurement.
    """

    # Input
    raw_note: str = ""
    patient_id: str | None = None
    payer: str | None = None

    # Workflow metadata
    workflow_id: str = ""
    status: WorkflowStatus = WorkflowStatus.PENDING
    started_at: float | None = None
    completed_at: float | None = None

    # Phase results
    documentation: PhaseResult = field(
        default_factory=lambda: PhaseResult(
            phase_name="documentation", agent_name="clinical_documentation"
        )
    )
    coding: PhaseResult = field(
        default_factory=lambda: PhaseResult(
            phase_name="coding", agent_name="medical_coding"
        )
    )
    compliance: PhaseResult = field(
        default_factory=lambda: PhaseResult(
            phase_name="compliance", agent_name="compliance"
        )
    )
    prior_auth: PhaseResult = field(
        default_factory=lambda: PhaseResult(
            phase_name="prior_auth", agent_name="prior_authorization"
        )
    )
    quality_assurance: PhaseResult = field(
        default_factory=lambda: PhaseResult(
            phase_name="quality_assurance", agent_name="quality_assurance"
        )
    )

    # Configuration
    skip_prior_auth: bool = False

    @property
    def total_duration_seconds(self) -> float | None:
        """Calculate total workflow duration."""
        if self.started_at is not None and self.completed_at is not None:
            return self.completed_at - self.started_at
        return None

    @property
    def total_tokens(self) -> dict[str, int]:
        """Calculate total token usage across all phases."""
        total_input = 0
        total_output = 0
        for phase in self.all_phases:
            total_input += phase.usage.get("input_tokens", 0)
            total_output += phase.usage.get("output_tokens", 0)
        return {"input_tokens": total_input, "output_tokens": total_output}

    @property
    def all_phases(self) -> list[PhaseResult]:
        """Get all phase results as a list."""
        return [
            self.documentation,
            self.coding,
            self.compliance,
            self.prior_auth,
            self.quality_assurance,
        ]

    @property
    def completed_phases(self) -> list[PhaseResult]:
        """Get only completed phase results."""
        return [p for p in self.all_phases if p.status == PhaseStatus.COMPLETED]

    @property
    def failed_phases(self) -> list[PhaseResult]:
        """Get only failed phase results."""
        return [p for p in self.all_phases if p.status == PhaseStatus.FAILED]

    def start(self) -> None:
        """Mark workflow as started."""
        self.status = WorkflowStatus.IN_PROGRESS
        self.started_at = time.monotonic()

    def complete(self) -> None:
        """Mark workflow as completed."""
        self.status = WorkflowStatus.COMPLETED
        self.completed_at = time.monotonic()

    def fail(self) -> None:
        """Mark workflow as failed."""
        self.status = WorkflowStatus.FAILED
        self.completed_at = time.monotonic()

    def to_summary(self) -> dict[str, Any]:
        """Generate a workflow summary dict."""
        return {
            "workflow_id": self.workflow_id,
            "status": self.status.value,
            "total_duration_seconds": self.total_duration_seconds,
            "total_tokens": self.total_tokens,
            "phases": {
                phase.phase_name: {
                    "status": phase.status.value,
                    "duration_seconds": phase.duration_seconds,
                    "has_error": phase.error is not None,
                }
                for phase in self.all_phases
            },
        }
