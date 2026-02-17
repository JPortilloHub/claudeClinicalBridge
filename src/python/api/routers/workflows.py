"""Workflow CRUD router — create, list, get, delete workflows."""

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.python.api import schemas
from src.python.api.dependencies import get_current_user
from src.python.api.models import (
    PhaseResult,
    PhaseStatus,
    User,
    Workflow,
    WorkflowStatus,
)
from src.python.utils.database import get_db

router = APIRouter(prefix="/api/workflows", tags=["workflows"])


@router.post("/", response_model=schemas.WorkflowDetail)
def create_workflow(
    request: schemas.WorkflowCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new workflow from a clinical note."""
    workflow = Workflow(
        raw_note=request.raw_note,
        patient_id=request.patient_id,
        payer=request.payer,
        procedure=request.procedure,
        skip_prior_auth=request.skip_prior_auth,
        created_by_user_id=current_user.id,
        status=WorkflowStatus.PENDING,
        current_phase="documentation",
    )
    db.add(workflow)
    db.flush()  # Get workflow.id

    # Create pending phase result entries
    phases = ["documentation", "coding", "compliance"]
    if request.payer and request.procedure and not request.skip_prior_auth:
        phases.append("prior_auth")
    phases.append("quality_assurance")

    for phase_name in phases:
        phase_result = PhaseResult(
            workflow_id=workflow.id,
            phase_name=phase_name,
            status=PhaseStatus.PENDING,
        )
        db.add(phase_result)

    db.commit()
    db.refresh(workflow)

    return workflow


@router.get("/", response_model=list[schemas.WorkflowSummary])
def list_workflows(
    status: str | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List workflows, optionally filtered by status."""
    query = db.query(Workflow)
    if status:
        query = query.filter(Workflow.status == status)

    workflows = (
        query.order_by(Workflow.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return workflows


@router.get("/{workflow_id}", response_model=schemas.WorkflowDetail)
def get_workflow(
    workflow_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a workflow with all phase results."""
    workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return workflow


@router.delete("/{workflow_id}")
def delete_workflow(
    workflow_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a workflow."""
    workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    db.delete(workflow)
    db.commit()

    return {"message": "Workflow deleted"}
