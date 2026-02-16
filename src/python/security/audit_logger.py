"""
HIPAA-compliant audit logger.

Records all access to patient data with timestamps, user identity,
action performed, and data accessed. Audit logs are retained for
the HIPAA-mandated minimum of 7 years.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from src.python.utils.config import settings
from src.python.utils.logging import get_logger

logger = get_logger(__name__)


class AuditAction(Enum):
    """Actions that generate audit log entries."""

    VIEW = "view"
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    EXPORT = "export"
    PROCESS = "process"       # Pipeline processing
    CODE_SUGGEST = "code_suggest"
    COMPLIANCE_CHECK = "compliance_check"
    PRIOR_AUTH = "prior_auth"
    QA_REVIEW = "qa_review"


class AuditOutcome(Enum):
    """Outcome of an audited action."""

    SUCCESS = "success"
    FAILURE = "failure"
    DENIED = "denied"


@dataclass
class AuditEntry:
    """A single HIPAA audit log entry."""

    timestamp: float
    action: str
    outcome: str
    agent_name: str = ""
    workflow_id: str = ""
    patient_id_hash: str = ""  # Never store raw patient ID
    resource_type: str = ""    # e.g., "clinical_note", "coding", "compliance"
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict())


class AuditLogger:
    """
    HIPAA-compliant audit logger.

    Writes structured audit entries to a dedicated log file separate
    from application logs. Entries are append-only and include
    hashed patient identifiers (never raw PHI).
    """

    def __init__(self, log_path: str | None = None):
        """
        Initialize the audit logger.

        Args:
            log_path: Path to audit log file (defaults to settings.audit_log_path)
        """
        self.log_path = Path(log_path or settings.audit_log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._entries: list[AuditEntry] = []

        logger.info(
            "audit_logger_initialized",
            log_path=str(self.log_path),
        )

    def log(
        self,
        action: AuditAction,
        outcome: AuditOutcome,
        agent_name: str = "",
        workflow_id: str = "",
        patient_id: str | None = None,
        resource_type: str = "",
        detail: str = "",
    ) -> AuditEntry:
        """
        Record an audit log entry.

        Args:
            action: The action being audited
            outcome: Whether the action succeeded
            agent_name: Name of the agent performing the action
            workflow_id: Workflow identifier for correlation
            patient_id: Raw patient ID (will be hashed before storage)
            resource_type: Type of resource accessed
            detail: Additional context (must not contain PHI)

        Returns:
            The created AuditEntry
        """
        entry = AuditEntry(
            timestamp=time.time(),
            action=action.value,
            outcome=outcome.value,
            agent_name=agent_name,
            workflow_id=workflow_id,
            patient_id_hash=_hash_identifier(patient_id) if patient_id else "",
            resource_type=resource_type,
            detail=detail,
        )

        self._entries.append(entry)
        self._write_entry(entry)

        logger.info(
            "audit_entry_recorded",
            action=action.value,
            outcome=outcome.value,
            agent_name=agent_name,
            resource_type=resource_type,
        )

        return entry

    def _write_entry(self, entry: AuditEntry) -> None:
        """Append an entry to the audit log file."""
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(entry.to_json() + "\n")

    @property
    def entry_count(self) -> int:
        """Number of entries recorded in this session."""
        return len(self._entries)

    def get_entries(
        self,
        action: AuditAction | None = None,
        workflow_id: str | None = None,
    ) -> list[AuditEntry]:
        """
        Query session entries with optional filters.

        Args:
            action: Filter by action type
            workflow_id: Filter by workflow ID

        Returns:
            Matching audit entries
        """
        results = self._entries

        if action is not None:
            results = [e for e in results if e.action == action.value]

        if workflow_id is not None:
            results = [e for e in results if e.workflow_id == workflow_id]

        return results


def _hash_identifier(identifier: str) -> str:
    """
    Hash a patient identifier for audit logging.

    Uses SHA-256 with a salt from settings to produce a consistent
    but irreversible hash for audit correlation.
    """
    import hashlib

    salt = settings.secret_key[:16]
    salted = f"{salt}:{identifier}"
    return hashlib.sha256(salted.encode()).hexdigest()[:16]
