"""Phase execution router — run, edit, and approve pipeline phases."""

from datetime import datetime, timezone
from threading import Thread
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
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
from src.python.orchestration.coordinator import (
    PHASE_ORDER,
    ClinicalPipelineCoordinator,
    get_next_phase,
)
from src.python.utils.database import SessionLocal, get_db
from src.python.utils.logging import get_logger

router = APIRouter(prefix="/api/workflows", tags=["phases"])

logger = get_logger(__name__)


def _run_phase_background(workflow_id: UUID, phase_name: str) -> None:
    """Background thread to run a single phase."""
    db = SessionLocal()
    try:
        workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
        if not workflow:
            logger.error("phase_bg_workflow_not_found", workflow_id=str(workflow_id))
            return

        phase_result = (
            db.query(PhaseResult)
            .filter(
                PhaseResult.workflow_id == workflow_id,
                PhaseResult.phase_name == phase_name,
            )
            .first()
        )
        if not phase_result:
            logger.error("phase_bg_result_not_found", phase=phase_name)
            return

        # Mark as running
        phase_result.status = PhaseStatus.RUNNING
        phase_result.started_at = datetime.now(timezone.utc)
        workflow.status = WorkflowStatus.IN_PROGRESS
        if not workflow.started_at:
            workflow.started_at = datetime.now(timezone.utc)
        db.commit()

        # Collect prior phase contents (use edited if available)
        phase_contents = {}
        for pr in workflow.phase_results:
            if pr.status == PhaseStatus.COMPLETED:
                phase_contents[pr.phase_name] = pr.edited_content or pr.content or ""

        # Run the phase
        coordinator = ClinicalPipelineCoordinator()
        result = coordinator.run_single_phase(
            phase_name=phase_name,
            raw_note=workflow.raw_note,
            phase_contents=phase_contents,
            patient_id=workflow.patient_id,
            payer=workflow.payer,
            procedure=workflow.procedure,
        )

        # Update phase result
        now = datetime.now(timezone.utc)
        if "error" in result:
            phase_result.status = PhaseStatus.FAILED
            phase_result.error = result["error"]
        else:
            phase_result.status = PhaseStatus.COMPLETED
            phase_result.content = result.get("content", "")
            phase_result.input_tokens = result.get("usage", {}).get("input_tokens", 0)
            phase_result.output_tokens = result.get("usage", {}).get("output_tokens", 0)

            # Update workflow totals
            workflow.total_input_tokens += phase_result.input_tokens or 0
            workflow.total_output_tokens += phase_result.output_tokens or 0

        phase_result.duration_seconds = result.get("duration_seconds")
        phase_result.completed_at = now

        # Update workflow status based on phase outcome
        if "error" in result:
            workflow.status = WorkflowStatus.IN_PROGRESS  # User can retry
        else:
            workflow.status = WorkflowStatus.NEEDS_REVIEW  # Awaiting human review

        db.commit()

        logger.info(
            "phase_bg_completed",
            workflow_id=str(workflow_id),
            phase=phase_name,
            status=phase_result.status.value,
        )

    except Exception as e:
        logger.error(
            "phase_bg_exception",
            workflow_id=str(workflow_id),
            phase=phase_name,
            error=str(e),
        )
        # Try to update the phase result status
        try:
            phase_result = (
                db.query(PhaseResult)
                .filter(
                    PhaseResult.workflow_id == workflow_id,
                    PhaseResult.phase_name == phase_name,
                )
                .first()
            )
            if phase_result:
                phase_result.status = PhaseStatus.FAILED
                phase_result.error = str(e)
                phase_result.completed_at = datetime.now(timezone.utc)
                db.commit()
        except Exception:
            pass
    finally:
        db.close()


@router.post("/{workflow_id}/phases/{phase_name}/run", response_model=schemas.PhaseRunResponse)
def run_phase(
    workflow_id: UUID,
    phase_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Start running a phase in the background."""
    if phase_name not in PHASE_ORDER:
        raise HTTPException(status_code=400, detail=f"Invalid phase: {phase_name}")

    workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    # Verify this is the current phase
    if workflow.current_phase != phase_name:
        raise HTTPException(
            status_code=400,
            detail=f"Current phase is '{workflow.current_phase}', not '{phase_name}'",
        )

    # Check phase isn't already running or completed
    phase_result = (
        db.query(PhaseResult)
        .filter(
            PhaseResult.workflow_id == workflow_id,
            PhaseResult.phase_name == phase_name,
        )
        .first()
    )
    if not phase_result:
        raise HTTPException(status_code=404, detail="Phase result not found")

    if phase_result.status == PhaseStatus.RUNNING:
        raise HTTPException(status_code=409, detail="Phase is already running")

    if phase_result.status == PhaseStatus.COMPLETED:
        raise HTTPException(status_code=409, detail="Phase is already completed")

    # Launch background thread
    thread = Thread(
        target=_run_phase_background,
        args=(workflow_id, phase_name),
        daemon=True,
    )
    thread.start()

    return schemas.PhaseRunResponse(
        message=f"Phase '{phase_name}' started",
        workflow_id=str(workflow_id),
        phase_name=phase_name,
    )


@router.get("/{workflow_id}/phases/{phase_name}", response_model=schemas.PhaseResultResponse)
def get_phase(
    workflow_id: UUID,
    phase_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a single phase result (for polling)."""
    phase_result = (
        db.query(PhaseResult)
        .filter(
            PhaseResult.workflow_id == workflow_id,
            PhaseResult.phase_name == phase_name,
        )
        .first()
    )
    if not phase_result:
        raise HTTPException(status_code=404, detail="Phase result not found")
    return phase_result


@router.patch("/{workflow_id}/phases/{phase_name}", response_model=schemas.PhaseResultResponse)
def edit_phase_content(
    workflow_id: UUID,
    phase_name: str,
    request: schemas.PhaseContentEdit,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Edit phase content (human review)."""
    phase_result = (
        db.query(PhaseResult)
        .filter(
            PhaseResult.workflow_id == workflow_id,
            PhaseResult.phase_name == phase_name,
        )
        .first()
    )
    if not phase_result:
        raise HTTPException(status_code=404, detail="Phase result not found")

    if phase_result.status != PhaseStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Can only edit completed phases")

    phase_result.edited_content = request.edited_content
    phase_result.reviewed_at = datetime.now(timezone.utc)
    phase_result.reviewed_by_user_id = current_user.id

    db.commit()
    db.refresh(phase_result)

    return phase_result


@router.post(
    "/{workflow_id}/phases/{phase_name}/approve", response_model=schemas.PhaseApproveResponse
)
def approve_phase(
    workflow_id: UUID,
    phase_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Approve a phase and advance workflow to next phase."""
    workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    phase_result = (
        db.query(PhaseResult)
        .filter(
            PhaseResult.workflow_id == workflow_id,
            PhaseResult.phase_name == phase_name,
        )
        .first()
    )
    if not phase_result:
        raise HTTPException(status_code=404, detail="Phase result not found")

    if phase_result.status != PhaseStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Phase must be completed before approval")

    # Mark as reviewed
    phase_result.reviewed_at = datetime.now(timezone.utc)
    phase_result.reviewed_by_user_id = current_user.id

    # Advance to next phase
    next_phase = get_next_phase(
        current_phase=phase_name,
        skip_prior_auth=workflow.skip_prior_auth,
        payer=workflow.payer,
        procedure=workflow.procedure,
    )

    if next_phase:
        workflow.current_phase = next_phase
        workflow.status = WorkflowStatus.PENDING
    else:
        # Final phase approved — workflow complete
        workflow.current_phase = "done"
        workflow.status = WorkflowStatus.COMPLETED
        workflow.completed_at = datetime.now(timezone.utc)

    db.commit()

    return schemas.PhaseApproveResponse(
        message=f"Phase '{phase_name}' approved",
        next_phase=next_phase,
    )
