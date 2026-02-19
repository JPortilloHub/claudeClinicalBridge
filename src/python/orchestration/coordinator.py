"""
Clinical Pipeline Coordinator.

Orchestrates multi-agent execution for processing clinical notes through
documentation, coding, compliance, prior authorization, and quality assurance.

Supports two execution modes:
1. Full pipeline: process_note() runs all phases sequentially (CLI)
2. Step-by-step: run_single_phase() runs one phase at a time (HITL UI)
"""

from __future__ import annotations

import time
import uuid
from typing import Any

import anthropic

from src.python.agents.clinical_documentation import ClinicalDocumentationAgent
from src.python.agents.compliance import ComplianceAgent
from src.python.agents.medical_coding import MedicalCodingAgent
from src.python.agents.prior_authorization import PriorAuthorizationAgent
from src.python.agents.quality_assurance import QualityAssuranceAgent
from src.python.orchestration.state import WorkflowState, WorkflowStatus
from src.python.orchestration.workflow import execute_phase
from src.python.utils.logging import get_logger

logger = get_logger(__name__)

# Phase execution order
PHASE_ORDER = ["documentation", "coding", "compliance", "prior_auth", "quality_assurance"]


def get_next_phase(
    current_phase: str, skip_prior_auth: bool, payer: str | None, procedure: str | None
) -> str | None:
    """Determine the next phase after the current one."""
    try:
        idx = PHASE_ORDER.index(current_phase)
    except ValueError:
        return None

    if idx >= len(PHASE_ORDER) - 1:
        return None  # Last phase

    next_phase = PHASE_ORDER[idx + 1]

    # Skip prior_auth if not needed
    if next_phase == "prior_auth" and (skip_prior_auth or not payer or not procedure):
        return "quality_assurance"

    return next_phase


class ClinicalPipelineCoordinator:
    """
    Coordinates the full clinical documentation and coding pipeline.

    Pipeline flow:
        Raw Note -> [Clinical Documentation] -> Structured SOAP
                 -> [Medical Coding]         -> ICD-10/CPT Codes
                 -> [Compliance]             -> Validation Results
                 -> [Prior Authorization]    -> Auth Assessment (if needed)
                 -> [Quality Assurance]      -> Final Review
    """

    def __init__(self, client: anthropic.Anthropic | None = None):
        """
        Initialize coordinator with all sub-agents.

        Args:
            client: Optional pre-configured Anthropic client shared across agents.
        """
        self.doc_agent = ClinicalDocumentationAgent(client=client)
        self.coding_agent = MedicalCodingAgent(client=client)
        self.compliance_agent = ComplianceAgent(client=client)
        self.prior_auth_agent = PriorAuthorizationAgent(client=client)
        self.qa_agent = QualityAssuranceAgent(client=client)

        logger.info("coordinator_initialized")

    def run_single_phase(
        self,
        phase_name: str,
        raw_note: str,
        phase_contents: dict[str, str],
        patient_id: str | None = None,
        payer: str | None = None,
        procedure: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Run a single pipeline phase and return the result.

        Used by the HITL UI to execute phases one at a time.
        Prior phase outputs are passed in via phase_contents, which allows
        the UI to substitute human-edited content.

        Args:
            phase_name: Which phase to run (documentation, coding, etc.)
            raw_note: The original clinical note text
            phase_contents: Dict mapping phase_name -> content string for completed phases
            patient_id: Optional patient identifier
            payer: Optional payer name
            procedure: Optional procedure description
            context: Optional additional context

        Returns:
            Dict with 'content', 'usage', 'agent', 'duration_seconds' keys.
            On error, includes 'error' key instead of 'content'.
        """
        # Build shared context
        shared_context = dict(context) if context else {}
        if patient_id:
            shared_context["patient_id"] = patient_id
        if payer:
            shared_context["payer"] = payer
        ctx = shared_context if shared_context else None

        logger.info(
            "single_phase_started",
            phase=phase_name,
            available_phases=list(phase_contents.keys()),
        )

        start = time.monotonic()

        try:
            if phase_name == "documentation":
                result = self.doc_agent.structure_note(raw_note, ctx)

            elif phase_name == "coding":
                doc_content = phase_contents.get("documentation", "")
                if not doc_content:
                    return {
                        "error": "Documentation phase must be completed first",
                        "agent": "medical_coding",
                    }
                result = self.coding_agent.suggest_codes(doc_content, ctx)

            elif phase_name == "compliance":
                doc_content = phase_contents.get("documentation", "")
                coding_content = phase_contents.get("coding", "")
                if not doc_content or not coding_content:
                    return {
                        "error": "Documentation and Coding phases must be completed first",
                        "agent": "compliance",
                    }
                result = self.compliance_agent.validate(doc_content, coding_content, ctx)

            elif phase_name == "prior_auth":
                doc_content = phase_contents.get("documentation", "")
                if not doc_content or not payer or not procedure:
                    return {
                        "error": "Documentation, payer, and procedure are required",
                        "agent": "prior_authorization",
                    }
                result = self.prior_auth_agent.assess_authorization(
                    procedure, payer, doc_content, ctx
                )

            elif phase_name == "quality_assurance":
                doc_content = phase_contents.get("documentation", "")
                coding_content = phase_contents.get("coding", "")
                compliance_content = phase_contents.get("compliance", "")
                if not doc_content or not coding_content:
                    return {
                        "error": "Prior phases must be completed first",
                        "agent": "quality_assurance",
                    }
                result = self.qa_agent.review(
                    raw_note, doc_content, coding_content, compliance_content, ctx
                )

            else:
                return {"error": f"Unknown phase: {phase_name}", "agent": "coordinator"}

        except Exception as e:
            duration = time.monotonic() - start
            logger.error(
                "single_phase_error",
                phase=phase_name,
                error=str(e),
                duration_seconds=duration,
            )
            return {"error": str(e), "agent": phase_name, "duration_seconds": duration}

        duration = time.monotonic() - start
        result["duration_seconds"] = duration

        logger.info(
            "single_phase_completed",
            phase=phase_name,
            duration_seconds=duration,
            has_error="error" in result,
        )

        return result

    def process_note(
        self,
        note: str,
        patient_id: str | None = None,
        payer: str | None = None,
        procedure: str | None = None,
        skip_prior_auth: bool = False,
        context: dict[str, Any] | None = None,
    ) -> WorkflowState:
        """
        Process a clinical note through the full pipeline.

        Args:
            note: Raw physician note text
            patient_id: Optional patient identifier
            payer: Optional payer name (required for prior auth)
            procedure: Optional procedure description (required for prior auth)
            skip_prior_auth: Skip prior authorization phase
            context: Optional additional context passed to all agents

        Returns:
            WorkflowState with results from all phases
        """
        state = WorkflowState(
            raw_note=note,
            patient_id=patient_id,
            payer=payer,
            workflow_id=str(uuid.uuid4()),
            skip_prior_auth=skip_prior_auth,
        )

        state.start()

        logger.info(
            "workflow_started",
            workflow_id=state.workflow_id,
            has_patient_id=patient_id is not None,
            payer=payer,
            skip_prior_auth=skip_prior_auth,
        )

        # Build shared context
        shared_context = dict(context) if context else {}
        if patient_id:
            shared_context["patient_id"] = patient_id
        if payer:
            shared_context["payer"] = payer

        ctx = shared_context if shared_context else None

        try:
            # Phase 1: Clinical Documentation
            doc_result = execute_phase(
                state.documentation,
                self.doc_agent.structure_note,
                note,
                ctx,
            )
            if "error" in doc_result:
                state.fail()
                return state

            # Phase 2: Medical Coding
            coding_result = execute_phase(
                state.coding,
                self.coding_agent.suggest_codes,
                doc_result["content"],
                ctx,
            )
            if "error" in coding_result:
                state.fail()
                return state

            # Phase 3: Compliance Validation
            compliance_result = execute_phase(
                state.compliance,
                self.compliance_agent.validate,
                doc_result["content"],
                coding_result["content"],
                ctx,
            )
            if "error" in compliance_result:
                state.fail()
                return state

            # Phase 4: Prior Authorization (conditional)
            if not skip_prior_auth and payer and procedure:
                execute_phase(
                    state.prior_auth,
                    self.prior_auth_agent.assess_authorization,
                    procedure,
                    payer,
                    doc_result["content"],
                    ctx,
                )
                # Prior auth failure is non-fatal — continue to QA
            else:
                state.prior_auth.mark_skipped()

            # Phase 5: Quality Assurance
            qa_result = execute_phase(
                state.quality_assurance,
                self.qa_agent.review,
                note,
                doc_result["content"],
                coding_result["content"],
                compliance_result["content"],
                ctx,
            )

            if "error" in qa_result:
                state.status = WorkflowStatus.NEEDS_REVIEW
            else:
                state.complete()

        except Exception as e:
            logger.error(
                "workflow_unexpected_error",
                workflow_id=state.workflow_id,
                error=str(e),
            )
            state.fail()

        logger.info(
            "workflow_finished",
            workflow_id=state.workflow_id,
            status=state.status.value,
            total_duration_seconds=state.total_duration_seconds,
            total_tokens=state.total_tokens,
        )

        return state
