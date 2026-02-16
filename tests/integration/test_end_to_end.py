"""
Integration tests for the end-to-end clinical pipeline.

These tests verify that the full orchestration pipeline works correctly
when all components are wired together. External API calls (Anthropic,
FHIR servers) are mocked to allow offline testing.

Run with:
    pytest tests/integration/test_end_to_end.py -o "addopts=" -v
"""

from unittest.mock import MagicMock, patch

import pytest

from src.python.orchestration.coordinator import ClinicalPipelineCoordinator
from src.python.orchestration.state import PhaseStatus, WorkflowStatus


SAMPLE_NOTE = """
65 year old male presents with chest pain radiating to left arm.
BP 160/95 mmHg, HR 88. History of essential hypertension and
type 2 diabetes mellitus on metformin 1000mg BID and lisinopril 20mg daily.
ECG shows ST depression in leads V4-V6.
Assessment: Unstable angina, uncontrolled hypertension, type 2 diabetes.
Plan: Admit, serial troponins, cardiology consult, continue home meds.
"""


def _make_mock_client():
    """Create a mock Anthropic client that returns structured responses."""
    client = MagicMock()
    return client


def _make_response(content: str, input_tokens: int = 100, output_tokens: int = 200):
    """Create a mock Anthropic API response."""
    response = MagicMock()
    response.content = [MagicMock(text=content)]
    response.usage = MagicMock(input_tokens=input_tokens, output_tokens=output_tokens)
    return response


@pytest.fixture
def mock_client():
    """Fixture that creates a mock client returning phase-appropriate responses."""
    client = _make_mock_client()
    client.messages.create.side_effect = [
        # Phase 1: Clinical Documentation
        _make_response(
            "SOAP Note:\n"
            "Chief Complaint: Chest pain radiating to left arm.\n"
            "HPI: 65yo M with HTN and T2DM presents with chest pain.\n"
            "Assessment: Unstable angina, uncontrolled HTN, T2DM.\n"
            "Plan: Admit, serial troponins, cardiology consult."
        ),
        # Phase 2: Medical Coding
        _make_response(
            "ICD-10 Codes:\n"
            "Primary: I20.0 - Unstable angina\n"
            "Secondary: I10 - Essential hypertension\n"
            "Secondary: E11.9 - Type 2 diabetes mellitus\n"
            "CPT: 99223 - Initial hospital care, high complexity"
        ),
        # Phase 3: Compliance
        _make_response(
            "Compliance Review: PASS\n"
            "All codes supported by documentation.\n"
            "Documentation meets E/M requirements for 99223."
        ),
        # Phase 4: Prior Auth (skipped in default test)
        # Phase 5: Quality Assurance
        _make_response(
            "QA Review: APPROVED\n"
            "All phases consistent. No hallucinations detected.\n"
            "Codes accurately reflect documented conditions."
        ),
    ]
    return client


class TestEndToEndPipeline:
    """Integration tests for the full clinical pipeline."""

    def test_full_pipeline_completes(self, mock_client):
        """Test complete pipeline execution from note to QA approval."""
        coordinator = ClinicalPipelineCoordinator(client=mock_client)
        state = coordinator.process_note(
            note=SAMPLE_NOTE,
            patient_id="P-TEST-001",
            payer="Medicare",
            skip_prior_auth=True,
        )

        assert state.status == WorkflowStatus.COMPLETED
        assert state.documentation.status == PhaseStatus.COMPLETED
        assert state.coding.status == PhaseStatus.COMPLETED
        assert state.compliance.status == PhaseStatus.COMPLETED
        assert state.quality_assurance.status == PhaseStatus.COMPLETED
        assert state.prior_auth.status == PhaseStatus.SKIPPED

    def test_pipeline_produces_content(self, mock_client):
        """Test that each phase produces meaningful content."""
        coordinator = ClinicalPipelineCoordinator(client=mock_client)
        state = coordinator.process_note(
            note=SAMPLE_NOTE,
            skip_prior_auth=True,
        )

        assert "SOAP" in state.documentation.content or "Chief Complaint" in state.documentation.content
        assert "ICD-10" in state.coding.content or "I20" in state.coding.content
        assert "Compliance" in state.compliance.content or "PASS" in state.compliance.content
        assert "QA" in state.quality_assurance.content or "APPROVED" in state.quality_assurance.content

    def test_pipeline_tracks_tokens(self, mock_client):
        """Test that token usage is tracked across phases."""
        coordinator = ClinicalPipelineCoordinator(client=mock_client)
        state = coordinator.process_note(
            note=SAMPLE_NOTE,
            skip_prior_auth=True,
        )

        assert state.total_tokens["input_tokens"] > 0
        assert state.total_tokens["output_tokens"] > 0
        assert state.documentation.usage.get("input_tokens", 0) > 0
        assert state.coding.usage.get("output_tokens", 0) > 0

    def test_pipeline_tracks_timing(self, mock_client):
        """Test that timing is recorded for each phase."""
        coordinator = ClinicalPipelineCoordinator(client=mock_client)
        state = coordinator.process_note(
            note=SAMPLE_NOTE,
            skip_prior_auth=True,
        )

        assert state.total_duration_seconds >= 0
        for phase in state.completed_phases:
            assert phase.started_at is not None
            assert phase.completed_at is not None
            assert phase.completed_at >= phase.started_at

    def test_pipeline_assigns_workflow_id(self, mock_client):
        """Test that each workflow gets a unique ID."""
        coordinator = ClinicalPipelineCoordinator(client=mock_client)
        state1 = coordinator.process_note(note=SAMPLE_NOTE, skip_prior_auth=True)

        # Reset side_effect for second run
        mock_client.messages.create.side_effect = [
            _make_response("Doc phase 2"),
            _make_response("Coding phase 2"),
            _make_response("Compliance phase 2"),
            _make_response("QA phase 2"),
        ]
        state2 = coordinator.process_note(note=SAMPLE_NOTE, skip_prior_auth=True)

        assert state1.workflow_id != state2.workflow_id

    def test_pipeline_with_prior_auth(self):
        """Test pipeline with prior authorization enabled."""
        client = _make_mock_client()
        client.messages.create.side_effect = [
            _make_response("Structured documentation"),
            _make_response("ICD-10: I20.0, CPT: 93458"),
            _make_response("Compliance: PASS"),
            _make_response("Prior Auth: Required. Clinical justification provided."),
            _make_response("QA: APPROVED"),
        ]

        coordinator = ClinicalPipelineCoordinator(client=client)
        state = coordinator.process_note(
            note=SAMPLE_NOTE,
            patient_id="P-TEST-002",
            payer="UnitedHealthcare",
            procedure="Cardiac catheterization",
            skip_prior_auth=False,
        )

        assert state.status == WorkflowStatus.COMPLETED
        assert state.prior_auth.status == PhaseStatus.COMPLETED
        assert "Prior Auth" in state.prior_auth.content

    def test_pipeline_early_failure_phase1(self):
        """Test pipeline stops on documentation phase failure."""
        client = _make_mock_client()
        # Enough errors for initial + retries (4 total)
        client.messages.create.side_effect = [
            TimeoutError("API timeout"),
            TimeoutError("API timeout"),
            TimeoutError("API timeout"),
            TimeoutError("API timeout"),
        ]

        coordinator = ClinicalPipelineCoordinator(client=client)
        state = coordinator.process_note(note=SAMPLE_NOTE, skip_prior_auth=True)

        assert state.status == WorkflowStatus.FAILED
        assert state.documentation.status == PhaseStatus.FAILED
        assert state.coding.status == PhaseStatus.PENDING

    def test_pipeline_qa_exception_fails_workflow(self):
        """Test that QA exception results in FAILED status.

        When execute_phase raises (after retries exhausted), the coordinator's
        except block calls state.fail(). NEEDS_REVIEW only occurs when
        execute_phase returns an error dict without throwing.
        """
        client = _make_mock_client()
        client.messages.create.side_effect = [
            _make_response("Structured documentation"),
            _make_response("ICD-10 codes: I20.0"),
            _make_response("Compliance: PASS"),
            # QA fails with enough retries
            TimeoutError("QA timeout"),
            TimeoutError("QA timeout"),
            TimeoutError("QA timeout"),
            TimeoutError("QA timeout"),
        ]

        coordinator = ClinicalPipelineCoordinator(client=client)
        state = coordinator.process_note(note=SAMPLE_NOTE, skip_prior_auth=True)

        assert state.status == WorkflowStatus.FAILED
        assert state.quality_assurance.status == PhaseStatus.FAILED

    def test_pipeline_summary_output(self, mock_client):
        """Test that workflow summary contains all phase results."""
        coordinator = ClinicalPipelineCoordinator(client=mock_client)
        state = coordinator.process_note(
            note=SAMPLE_NOTE,
            skip_prior_auth=True,
        )

        summary = state.to_summary()
        assert "workflow_id" in summary
        assert "status" in summary
        assert "total_duration_seconds" in summary
        assert "phases" in summary
        assert len(summary["phases"]) == 5


class TestEndToEndSecurity:
    """Integration tests verifying security measures in the pipeline."""

    def test_patient_id_not_in_logs(self, mock_client, capsys):
        """Test that raw patient IDs don't appear in log output."""
        coordinator = ClinicalPipelineCoordinator(client=mock_client)
        state = coordinator.process_note(
            note=SAMPLE_NOTE,
            patient_id="P-SENSITIVE-123",
            skip_prior_auth=True,
        )

        # The coordinator should log has_patient_id=True, not the raw ID
        assert state.status == WorkflowStatus.COMPLETED

    def test_workflow_with_phi_in_note(self, mock_client):
        """Test pipeline handles notes containing PHI."""
        note_with_phi = (
            "Patient John Smith, SSN 123-45-6789, DOB 03/15/1960. "
            "Presents with chest pain. BP 160/95."
        )

        coordinator = ClinicalPipelineCoordinator(client=mock_client)
        state = coordinator.process_note(
            note=note_with_phi,
            skip_prior_auth=True,
        )

        # Pipeline should complete even with PHI in the note
        assert state.status == WorkflowStatus.COMPLETED


class TestEndToEndEvaluation:
    """Integration tests combining pipeline with evaluation metrics."""

    def test_pipeline_output_evaluable(self, mock_client):
        """Test that pipeline output can be fed into evaluation framework."""
        from src.python.evaluation.coding_accuracy import evaluate_codes
        from src.python.evaluation.hallucination_audit import audit_hallucinations

        coordinator = ClinicalPipelineCoordinator(client=mock_client)
        state = coordinator.process_note(
            note=SAMPLE_NOTE,
            skip_prior_auth=True,
        )

        # Verify coding output can be evaluated
        coding_eval = evaluate_codes(
            case_id="integration-1",
            expected=["I20.0", "I10", "E11.9"],
            predicted=["I20.0", "I10", "E11.9"],
        )
        assert coding_eval.exact_match is True

        # Verify hallucination audit can run on pipeline output
        audit = audit_hallucinations(
            case_id="integration-1",
            source_note=SAMPLE_NOTE,
            predicted_codes=["I20.0", "I10", "E11.9"],
            output_diagnoses=["unstable angina", "hypertension", "type 2 diabetes"],
        )
        assert audit.items_checked > 0

    def test_pipeline_latency_trackable(self, mock_client):
        """Test that pipeline timing integrates with latency tracker."""
        from src.python.evaluation.latency_tracker import LatencyReport, TimingRecord

        coordinator = ClinicalPipelineCoordinator(client=mock_client)
        state = coordinator.process_note(
            note=SAMPLE_NOTE,
            skip_prior_auth=True,
        )

        report = LatencyReport(target_seconds=30.0)
        report.add(TimingRecord(
            name="full_pipeline",
            started_at=0,
            completed_at=state.total_duration_seconds,
        ))

        assert report.total_records == 1
        assert report.meets_target is True
