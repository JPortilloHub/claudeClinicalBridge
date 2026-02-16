"""
Unit tests for the orchestration layer.

Tests cover:
- WorkflowState and PhaseResult state management
- Retry logic with exponential backoff
- Phase execution with state tracking
- ClinicalPipelineCoordinator end-to-end flow
"""

from unittest.mock import MagicMock, patch

import pytest

from src.python.orchestration.coordinator import ClinicalPipelineCoordinator
from src.python.orchestration.state import (
    PhaseResult,
    PhaseStatus,
    WorkflowState,
    WorkflowStatus,
)
from src.python.orchestration.workflow import execute_phase, run_with_retry


# ============================================================================
# Fixtures
# ============================================================================


def _make_agent_result(content: str = '{"result": "ok"}', agent: str = "test") -> dict:
    """Create a standard agent result dict."""
    return {
        "content": content,
        "agent": agent,
        "model": "claude-opus-4-6",
        "usage": {"input_tokens": 100, "output_tokens": 50},
        "stop_reason": "end_turn",
    }


def _make_error_result(agent: str = "test", error: str = "Request timed out") -> dict:
    """Create an agent error result dict."""
    return {"content": "", "agent": agent, "error": error}


@pytest.fixture
def mock_anthropic_client():
    """Mock Anthropic client with standard response."""
    client = MagicMock()
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text='{"result": "test output"}')]
    mock_response.model = "claude-opus-4-6"
    mock_response.usage.input_tokens = 100
    mock_response.usage.output_tokens = 50
    mock_response.stop_reason = "end_turn"
    client.messages.create.return_value = mock_response
    return client


# ============================================================================
# PhaseResult Tests
# ============================================================================


def test_phase_result_initial_state():
    """Test PhaseResult starts in PENDING status."""
    phase = PhaseResult(phase_name="test", agent_name="test_agent")

    assert phase.status == PhaseStatus.PENDING
    assert phase.content == ""
    assert phase.error is None
    assert phase.duration_seconds is None


def test_phase_result_mark_running():
    """Test marking a phase as running sets start time."""
    phase = PhaseResult(phase_name="test", agent_name="test_agent")
    phase.mark_running()

    assert phase.status == PhaseStatus.RUNNING
    assert phase.started_at is not None


def test_phase_result_mark_completed():
    """Test marking a phase as completed stores results."""
    phase = PhaseResult(phase_name="test", agent_name="test_agent")
    phase.mark_running()
    phase.mark_completed(content="result data", usage={"input_tokens": 10, "output_tokens": 5})

    assert phase.status == PhaseStatus.COMPLETED
    assert phase.content == "result data"
    assert phase.usage == {"input_tokens": 10, "output_tokens": 5}
    assert phase.duration_seconds is not None
    assert phase.duration_seconds >= 0


def test_phase_result_mark_failed():
    """Test marking a phase as failed stores error."""
    phase = PhaseResult(phase_name="test", agent_name="test_agent")
    phase.mark_running()
    phase.mark_failed("API timeout")

    assert phase.status == PhaseStatus.FAILED
    assert phase.error == "API timeout"
    assert phase.completed_at is not None


def test_phase_result_mark_skipped():
    """Test marking a phase as skipped."""
    phase = PhaseResult(phase_name="test", agent_name="test_agent")
    phase.mark_skipped()

    assert phase.status == PhaseStatus.SKIPPED
    assert phase.completed_at is not None


# ============================================================================
# WorkflowState Tests
# ============================================================================


def test_workflow_state_initial():
    """Test WorkflowState initial values."""
    state = WorkflowState(raw_note="Test note", patient_id="P123")

    assert state.status == WorkflowStatus.PENDING
    assert state.raw_note == "Test note"
    assert state.patient_id == "P123"
    assert len(state.all_phases) == 5
    assert all(p.status == PhaseStatus.PENDING for p in state.all_phases)


def test_workflow_state_start_and_complete():
    """Test workflow start and complete lifecycle."""
    state = WorkflowState()
    state.start()

    assert state.status == WorkflowStatus.IN_PROGRESS
    assert state.started_at is not None

    state.complete()

    assert state.status == WorkflowStatus.COMPLETED
    assert state.total_duration_seconds is not None
    assert state.total_duration_seconds >= 0


def test_workflow_state_fail():
    """Test workflow failure."""
    state = WorkflowState()
    state.start()
    state.fail()

    assert state.status == WorkflowStatus.FAILED
    assert state.total_duration_seconds is not None


def test_workflow_state_total_tokens():
    """Test total token aggregation across phases."""
    state = WorkflowState()
    state.documentation.mark_running()
    state.documentation.mark_completed("doc", {"input_tokens": 100, "output_tokens": 50})
    state.coding.mark_running()
    state.coding.mark_completed("code", {"input_tokens": 200, "output_tokens": 100})

    tokens = state.total_tokens
    assert tokens["input_tokens"] == 300
    assert tokens["output_tokens"] == 150


def test_workflow_state_completed_and_failed_phases():
    """Test phase filtering properties."""
    state = WorkflowState()
    state.documentation.mark_running()
    state.documentation.mark_completed("ok", {})
    state.coding.mark_running()
    state.coding.mark_failed("timeout")

    assert len(state.completed_phases) == 1
    assert len(state.failed_phases) == 1
    assert state.completed_phases[0].phase_name == "documentation"
    assert state.failed_phases[0].phase_name == "coding"


def test_workflow_state_to_summary():
    """Test summary generation."""
    state = WorkflowState(workflow_id="test-123")
    state.start()
    state.documentation.mark_running()
    state.documentation.mark_completed("ok", {"input_tokens": 50, "output_tokens": 25})
    state.complete()

    summary = state.to_summary()

    assert summary["workflow_id"] == "test-123"
    assert summary["status"] == "completed"
    assert summary["total_duration_seconds"] is not None
    assert summary["phases"]["documentation"]["status"] == "completed"
    assert summary["phases"]["coding"]["status"] == "pending"


# ============================================================================
# run_with_retry Tests
# ============================================================================


@patch("src.python.orchestration.workflow.time.sleep")
def test_retry_success_first_attempt(mock_sleep):
    """Test no retry when first attempt succeeds."""
    fn = MagicMock(return_value=_make_agent_result())

    result = run_with_retry(fn, "arg1", max_retries=3)

    assert "error" not in result
    assert fn.call_count == 1
    mock_sleep.assert_not_called()


@patch("src.python.orchestration.workflow.time.sleep")
def test_retry_success_after_failures(mock_sleep):
    """Test successful retry after initial failures."""
    fn = MagicMock(
        side_effect=[
            _make_error_result(error="timeout"),
            _make_error_result(error="timeout"),
            _make_agent_result(),
        ]
    )

    result = run_with_retry(fn, "arg1", max_retries=3, base_delay=0.1)

    assert "error" not in result
    assert fn.call_count == 3
    assert mock_sleep.call_count == 2


@patch("src.python.orchestration.workflow.time.sleep")
def test_retry_all_attempts_fail(mock_sleep):
    """Test returns last error when all retries exhausted."""
    fn = MagicMock(return_value=_make_error_result(error="persistent error"))

    result = run_with_retry(fn, max_retries=2, base_delay=0.1)

    assert "error" in result
    assert result["error"] == "persistent error"
    assert fn.call_count == 3  # initial + 2 retries
    assert mock_sleep.call_count == 2


@patch("src.python.orchestration.workflow.time.sleep")
def test_retry_exponential_backoff(mock_sleep):
    """Test delay doubles each retry attempt."""
    fn = MagicMock(return_value=_make_error_result())

    run_with_retry(fn, max_retries=3, base_delay=1.0)

    delays = [call.args[0] for call in mock_sleep.call_args_list]
    assert delays == [1.0, 2.0, 4.0]


# ============================================================================
# execute_phase Tests
# ============================================================================


def test_execute_phase_success():
    """Test phase execution on success."""
    phase = PhaseResult(phase_name="test", agent_name="test_agent")
    fn = MagicMock(return_value=_make_agent_result(content="phase output"))

    result = execute_phase(phase, fn, "input", use_retry=False)

    assert phase.status == PhaseStatus.COMPLETED
    assert phase.content == "phase output"
    assert phase.duration_seconds is not None
    assert "error" not in result


def test_execute_phase_failure():
    """Test phase execution on failure."""
    phase = PhaseResult(phase_name="test", agent_name="test_agent")
    fn = MagicMock(return_value=_make_error_result(error="API error"))

    result = execute_phase(phase, fn, "input", use_retry=False)

    assert phase.status == PhaseStatus.FAILED
    assert phase.error == "API error"
    assert "error" in result


@patch("src.python.orchestration.workflow.time.sleep")
def test_execute_phase_with_retry(mock_sleep):
    """Test phase execution uses retry when enabled."""
    phase = PhaseResult(phase_name="test", agent_name="test_agent")
    fn = MagicMock(
        side_effect=[
            _make_error_result(error="timeout"),
            _make_agent_result(content="retry success"),
        ]
    )

    result = execute_phase(phase, fn, "input", use_retry=True, max_retries=2, base_delay=0.1)

    assert phase.status == PhaseStatus.COMPLETED
    assert phase.content == "retry success"
    assert fn.call_count == 2


# ============================================================================
# ClinicalPipelineCoordinator Tests
# ============================================================================


def test_coordinator_initialization(mock_anthropic_client):
    """Test coordinator initializes all 5 agents."""
    coordinator = ClinicalPipelineCoordinator(client=mock_anthropic_client)

    assert coordinator.doc_agent is not None
    assert coordinator.coding_agent is not None
    assert coordinator.compliance_agent is not None
    assert coordinator.prior_auth_agent is not None
    assert coordinator.qa_agent is not None


def test_coordinator_full_pipeline(mock_anthropic_client):
    """Test full pipeline execution with all phases."""
    coordinator = ClinicalPipelineCoordinator(client=mock_anthropic_client)

    state = coordinator.process_note(
        note="Patient presents with chest pain.",
        patient_id="P001",
        payer="Medicare",
        procedure="99214",
    )

    assert state.status == WorkflowStatus.COMPLETED
    assert state.workflow_id != ""
    assert state.documentation.status == PhaseStatus.COMPLETED
    assert state.coding.status == PhaseStatus.COMPLETED
    assert state.compliance.status == PhaseStatus.COMPLETED
    assert state.prior_auth.status == PhaseStatus.COMPLETED
    assert state.quality_assurance.status == PhaseStatus.COMPLETED
    assert state.total_duration_seconds is not None

    # Verify all 5 agents were called
    assert mock_anthropic_client.messages.create.call_count == 5


def test_coordinator_skip_prior_auth(mock_anthropic_client):
    """Test pipeline with prior auth skipped."""
    coordinator = ClinicalPipelineCoordinator(client=mock_anthropic_client)

    state = coordinator.process_note(
        note="Patient presents with headache.",
        skip_prior_auth=True,
    )

    assert state.status == WorkflowStatus.COMPLETED
    assert state.prior_auth.status == PhaseStatus.SKIPPED
    # 4 agents called (no prior auth)
    assert mock_anthropic_client.messages.create.call_count == 4


def test_coordinator_no_payer_skips_prior_auth(mock_anthropic_client):
    """Test pipeline auto-skips prior auth when no payer specified."""
    coordinator = ClinicalPipelineCoordinator(client=mock_anthropic_client)

    state = coordinator.process_note(note="Simple visit note.")

    assert state.prior_auth.status == PhaseStatus.SKIPPED
    assert mock_anthropic_client.messages.create.call_count == 4


def test_coordinator_doc_phase_failure(mock_anthropic_client):
    """Test pipeline stops on documentation phase failure."""
    import anthropic as anthropic_mod

    mock_anthropic_client.messages.create.side_effect = anthropic_mod.APITimeoutError(
        request=MagicMock()
    )

    coordinator = ClinicalPipelineCoordinator(client=mock_anthropic_client)

    state = coordinator.process_note(note="Test note.")

    assert state.status == WorkflowStatus.FAILED
    assert state.documentation.status == PhaseStatus.FAILED
    assert state.coding.status == PhaseStatus.PENDING


def test_coordinator_coding_phase_failure(mock_anthropic_client):
    """Test pipeline stops on coding phase failure."""
    import anthropic as anthropic_mod

    # First call succeeds (documentation), second fails (coding)
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text='{"result": "ok"}')]
    mock_response.model = "claude-opus-4-6"
    mock_response.usage.input_tokens = 100
    mock_response.usage.output_tokens = 50
    mock_response.stop_reason = "end_turn"

    # Need enough timeout errors for initial attempt + retries (default max_retries=3)
    mock_anthropic_client.messages.create.side_effect = [
        mock_response,
        anthropic_mod.APITimeoutError(request=MagicMock()),
        anthropic_mod.APITimeoutError(request=MagicMock()),
        anthropic_mod.APITimeoutError(request=MagicMock()),
        anthropic_mod.APITimeoutError(request=MagicMock()),
    ]

    coordinator = ClinicalPipelineCoordinator(client=mock_anthropic_client)

    state = coordinator.process_note(note="Test note.")

    assert state.status == WorkflowStatus.FAILED
    assert state.documentation.status == PhaseStatus.COMPLETED
    assert state.coding.status == PhaseStatus.FAILED
    assert state.compliance.status == PhaseStatus.PENDING


def test_coordinator_context_passed(mock_anthropic_client):
    """Test that context is passed through to agents."""
    coordinator = ClinicalPipelineCoordinator(client=mock_anthropic_client)

    state = coordinator.process_note(
        note="Test note.",
        patient_id="P123",
        payer="Aetna",
        context={"encounter_type": "office_visit"},
    )

    assert state.status == WorkflowStatus.COMPLETED

    # Verify context was included in the first API call
    first_call = mock_anthropic_client.messages.create.call_args_list[0]
    user_message = first_call.kwargs["messages"][0]["content"]
    assert "patient_id" in user_message
    assert "P123" in user_message
    assert "encounter_type" in user_message


def test_coordinator_summary_output(mock_anthropic_client):
    """Test workflow state summary after completion."""
    coordinator = ClinicalPipelineCoordinator(client=mock_anthropic_client)

    state = coordinator.process_note(note="Test note.")
    summary = state.to_summary()

    assert summary["status"] == "completed"
    assert summary["total_duration_seconds"] is not None
    assert summary["total_tokens"]["input_tokens"] > 0
    assert summary["total_tokens"]["output_tokens"] > 0
    assert len(summary["phases"]) == 5
