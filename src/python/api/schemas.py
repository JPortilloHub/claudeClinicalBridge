"""Pydantic schemas for API request/response validation."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

# --- Auth ---


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserResponse"


class UserResponse(BaseModel):
    id: int
    username: str
    full_name: str | None
    role: str

    class Config:
        from_attributes = True


# --- Workflows ---


class WorkflowCreate(BaseModel):
    raw_note: str
    patient_id: str | None = None
    payer: str | None = None
    procedure: str | None = None
    skip_prior_auth: bool = False


class PhaseResultResponse(BaseModel):
    id: int
    phase_name: str
    status: str
    content: str | None
    edited_content: str | None
    error: str | None
    input_tokens: int | None
    output_tokens: int | None
    duration_seconds: float | None
    reviewed_at: datetime | None

    class Config:
        from_attributes = True


class WorkflowSummary(BaseModel):
    id: UUID
    created_at: datetime
    status: str
    current_phase: str | None
    raw_note: str
    patient_id: str | None
    payer: str | None
    procedure: str | None
    total_input_tokens: int
    total_output_tokens: int

    class Config:
        from_attributes = True


class WorkflowDetail(BaseModel):
    id: UUID
    created_at: datetime
    updated_at: datetime
    status: str
    current_phase: str | None
    raw_note: str
    patient_id: str | None
    payer: str | None
    procedure: str | None
    skip_prior_auth: bool
    total_input_tokens: int
    total_output_tokens: int
    started_at: datetime | None
    completed_at: datetime | None
    phase_results: list[PhaseResultResponse]

    class Config:
        from_attributes = True


# --- Phase operations ---


class PhaseContentEdit(BaseModel):
    edited_content: str


class PhaseRunResponse(BaseModel):
    message: str
    workflow_id: str
    phase_name: str


class PhaseApproveResponse(BaseModel):
    message: str
    next_phase: str | None
