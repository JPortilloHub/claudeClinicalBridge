"""SQLAlchemy models for workflow persistence."""

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy import (
    Enum as SQLEnum,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from src.python.utils.database import Base


def _utcnow():
    """Return current UTC time (non-deprecated replacement for _utcnow)."""
    return datetime.now(timezone.utc)


class WorkflowStatus(str, enum.Enum):
    """Workflow status enum."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    NEEDS_REVIEW = "needs_review"
    COMPLETED = "completed"
    FAILED = "failed"


class PhaseStatus(str, enum.Enum):
    """Phase execution status enum."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class User(Base):
    """User model for authentication."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255))
    role = Column(String(50), default="reviewer")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=_utcnow)


class Workflow(Base):
    """Workflow model representing a clinical note processing session."""

    __tablename__ = "workflows"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime, default=_utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow, nullable=False)
    created_by_user_id = Column(Integer, ForeignKey("users.id"))

    status = Column(
        SQLEnum(WorkflowStatus),
        nullable=False,
        default=WorkflowStatus.PENDING,
        index=True,
    )
    current_phase = Column(String(20))

    # Input data
    raw_note = Column(Text, nullable=False)
    patient_id = Column(String(100))
    payer = Column(String(100))
    procedure = Column(String(100))
    skip_prior_auth = Column(Boolean, default=False)

    # Metrics
    total_input_tokens = Column(Integer, default=0)
    total_output_tokens = Column(Integer, default=0)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)

    # Relationships
    phase_results = relationship(
        "PhaseResult", back_populates="workflow", cascade="all, delete-orphan"
    )
    created_by = relationship("User")


class PhaseResult(Base):
    """Phase result model representing output from a single pipeline phase."""

    __tablename__ = "phase_results"

    id = Column(Integer, primary_key=True)
    workflow_id = Column(
        UUID(as_uuid=True),
        ForeignKey("workflows.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    phase_name = Column(String(20), nullable=False)

    status = Column(SQLEnum(PhaseStatus), nullable=False, default=PhaseStatus.PENDING)
    content = Column(Text)  # Original agent output (JSON string)
    edited_content = Column(Text)  # Human-edited version (JSON string)
    error = Column(Text)

    # Metrics
    input_tokens = Column(Integer)
    output_tokens = Column(Integer)
    duration_seconds = Column(Float)

    # Timestamps
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    reviewed_at = Column(DateTime)
    reviewed_by_user_id = Column(Integer, ForeignKey("users.id"))

    # Relationships
    workflow = relationship("Workflow", back_populates="phase_results")
    reviewed_by = relationship("User")
