"""
Unit tests for Claude Agent SDK sub-agents.

All tests mock the Anthropic API to avoid real API calls.
"""

from unittest.mock import MagicMock

import pytest

from src.python.agents.base_agent import BaseAgent
from src.python.agents.clinical_documentation import ClinicalDocumentationAgent
from src.python.agents.compliance import ComplianceAgent
from src.python.agents.medical_coding import MedicalCodingAgent
from src.python.agents.prior_authorization import PriorAuthorizationAgent
from src.python.agents.quality_assurance import QualityAssuranceAgent

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_anthropic_client():
    """Create a mock Anthropic client with standard response."""
    client = MagicMock()

    # Mock response structure
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text='{"result": "test output"}')]
    mock_response.model = "claude-opus-4-6"
    mock_response.usage.input_tokens = 100
    mock_response.usage.output_tokens = 50
    mock_response.stop_reason = "end_turn"

    client.messages.create.return_value = mock_response
    return client


@pytest.fixture
def mock_client_timeout():
    """Create a mock client that raises a timeout error."""
    import anthropic

    client = MagicMock()
    client.messages.create.side_effect = anthropic.APITimeoutError(request=MagicMock())
    return client


@pytest.fixture
def mock_client_api_error():
    """Create a mock client that raises an API error."""
    import anthropic

    client = MagicMock()
    client.messages.create.side_effect = anthropic.APIStatusError(
        message="Internal server error",
        response=MagicMock(status_code=500),
        body={"error": {"message": "Internal server error"}},
    )
    return client


# ============================================================================
# BaseAgent Tests
# ============================================================================


def test_base_agent_initialization(mock_anthropic_client):
    """Test base agent initializes with mock client."""
    agent = BaseAgent(client=mock_anthropic_client)

    assert agent.agent_name == "base_agent"
    assert agent.client is mock_anthropic_client
    assert agent._system_prompt is not None


def test_base_agent_run(mock_anthropic_client):
    """Test base agent run returns structured result."""
    agent = BaseAgent(client=mock_anthropic_client)
    result = agent.run("Test prompt")

    assert result["content"] == '{"result": "test output"}'
    assert result["agent"] == "base_agent"
    assert result["usage"]["input_tokens"] == 100
    assert result["usage"]["output_tokens"] == 50
    assert result["stop_reason"] == "end_turn"
    assert "error" not in result


def test_base_agent_run_with_context(mock_anthropic_client):
    """Test base agent run with context dict."""
    agent = BaseAgent(client=mock_anthropic_client)
    result = agent.run("Test prompt", context={"patient_id": "12345", "payer": "Medicare"})

    assert result["content"] == '{"result": "test output"}'

    # Verify the messages include context
    call_args = mock_anthropic_client.messages.create.call_args
    user_message = call_args.kwargs["messages"][0]["content"]
    assert "## Context" in user_message
    assert "patient_id" in user_message
    assert "## Task" in user_message


def test_base_agent_timeout(mock_client_timeout):
    """Test base agent handles timeout gracefully."""
    agent = BaseAgent(client=mock_client_timeout)
    result = agent.run("Test prompt")

    assert result["content"] == ""
    assert "error" in result
    assert "timed out" in result["error"]


def test_base_agent_api_error(mock_client_api_error):
    """Test base agent handles API errors gracefully."""
    agent = BaseAgent(client=mock_client_api_error)
    result = agent.run("Test prompt")

    assert result["content"] == ""
    assert "error" in result
    assert "API error" in result["error"]


def test_base_agent_build_messages(mock_anthropic_client):
    """Test message building without context."""
    agent = BaseAgent(client=mock_anthropic_client)
    messages = agent._build_messages("Hello")

    assert len(messages) == 1
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "Hello"


def test_base_agent_build_messages_with_context(mock_anthropic_client):
    """Test message building with context."""
    agent = BaseAgent(client=mock_anthropic_client)
    messages = agent._build_messages("Analyze this", context={"key": "value"})

    assert len(messages) == 1
    assert "## Context" in messages[0]["content"]
    assert "**key**: value" in messages[0]["content"]
    assert "## Task" in messages[0]["content"]
    assert "Analyze this" in messages[0]["content"]


# ============================================================================
# ClinicalDocumentationAgent Tests
# ============================================================================


def test_clinical_doc_agent_init(mock_anthropic_client):
    """Test ClinicalDocumentationAgent initialization."""
    agent = ClinicalDocumentationAgent(client=mock_anthropic_client)

    assert agent.agent_name == "clinical_documentation"
    assert agent.required_skills == ("medical_terminology", "clinical_reasoning")
    assert "SOAP" in agent._system_prompt
    assert "Medical Terminology" in agent._system_prompt
    assert "Clinical Reasoning" in agent._system_prompt


def test_clinical_doc_agent_structure_note(mock_anthropic_client):
    """Test structuring a physician note."""
    agent = ClinicalDocumentationAgent(client=mock_anthropic_client)
    result = agent.structure_note("Patient presents with chest pain, SOB since yesterday.")

    assert result["agent"] == "clinical_documentation"
    assert result["content"] == '{"result": "test output"}'
    assert "error" not in result

    # Verify the prompt includes the note
    call_args = mock_anthropic_client.messages.create.call_args
    user_message = call_args.kwargs["messages"][0]["content"]
    assert "chest pain" in user_message


# ============================================================================
# MedicalCodingAgent Tests
# ============================================================================


def test_medical_coding_agent_init(mock_anthropic_client):
    """Test MedicalCodingAgent initialization."""
    agent = MedicalCodingAgent(client=mock_anthropic_client)

    assert agent.agent_name == "medical_coding"
    assert agent.required_skills == ("coding_accuracy", "medical_terminology")
    assert "ICD-10" in agent._system_prompt
    assert "CPT" in agent._system_prompt


def test_medical_coding_agent_suggest_codes(mock_anthropic_client):
    """Test code suggestion."""
    agent = MedicalCodingAgent(client=mock_anthropic_client)
    result = agent.suggest_codes("Assessment: Primary osteoarthritis, right knee")

    assert result["agent"] == "medical_coding"
    assert "error" not in result


# ============================================================================
# ComplianceAgent Tests
# ============================================================================


def test_compliance_agent_init(mock_anthropic_client):
    """Test ComplianceAgent initialization."""
    agent = ComplianceAgent(client=mock_anthropic_client)

    assert agent.agent_name == "compliance"
    assert agent.required_skills == ("regulatory_compliance", "coding_accuracy")
    assert "HIPAA" in agent._system_prompt or "compliance" in agent._system_prompt.lower()


def test_compliance_agent_validate(mock_anthropic_client):
    """Test compliance validation."""
    agent = ComplianceAgent(client=mock_anthropic_client)
    result = agent.validate(
        documentation="SOAP note content...",
        suggested_codes="M17.11, 99214",
    )

    assert result["agent"] == "compliance"
    assert "error" not in result


# ============================================================================
# PriorAuthorizationAgent Tests
# ============================================================================


def test_prior_auth_agent_init(mock_anthropic_client):
    """Test PriorAuthorizationAgent initialization."""
    agent = PriorAuthorizationAgent(client=mock_anthropic_client)

    assert agent.agent_name == "prior_authorization"
    assert agent.required_skills == ("regulatory_compliance", "clinical_reasoning")
    assert "prior auth" in agent._system_prompt.lower()


def test_prior_auth_agent_assess(mock_anthropic_client):
    """Test prior authorization assessment."""
    agent = PriorAuthorizationAgent(client=mock_anthropic_client)
    result = agent.assess_authorization(
        procedure="27447 - Total knee arthroplasty",
        payer="Aetna",
        clinical_data="6 months PT, failed conservative management, KL grade 4",
    )

    assert result["agent"] == "prior_authorization"
    assert "error" not in result

    # Verify prompt includes all inputs
    call_args = mock_anthropic_client.messages.create.call_args
    user_message = call_args.kwargs["messages"][0]["content"]
    assert "27447" in user_message
    assert "Aetna" in user_message
    assert "conservative management" in user_message


# ============================================================================
# QualityAssuranceAgent Tests
# ============================================================================


def test_qa_agent_init(mock_anthropic_client):
    """Test QualityAssuranceAgent initialization."""
    agent = QualityAssuranceAgent(client=mock_anthropic_client)

    assert agent.agent_name == "quality_assurance"
    assert len(agent.required_skills) == 4
    assert "medical_terminology" in agent.required_skills
    assert "coding_accuracy" in agent.required_skills
    assert "clinical_reasoning" in agent.required_skills
    assert "regulatory_compliance" in agent.required_skills
    assert "hallucination" in agent._system_prompt.lower()


def test_qa_agent_review(mock_anthropic_client):
    """Test quality assurance review."""
    agent = QualityAssuranceAgent(client=mock_anthropic_client)
    result = agent.review(
        source_note="Patient has right knee pain x 6 months",
        documentation="SOAP structured note...",
        coding="M17.11, 99214",
        compliance="All checks passed",
    )

    assert result["agent"] == "quality_assurance"
    assert "error" not in result

    # Verify prompt includes all pipeline outputs
    call_args = mock_anthropic_client.messages.create.call_args
    user_message = call_args.kwargs["messages"][0]["content"]
    assert "Original Physician Note" in user_message
    assert "Structured Documentation" in user_message
    assert "Coding Suggestions" in user_message
    assert "Compliance Validation" in user_message


# ============================================================================
# Integration / Cross-Agent Tests
# ============================================================================


def test_all_agents_share_base_class(mock_anthropic_client):
    """Test all agents inherit from BaseAgent."""
    agents = [
        ClinicalDocumentationAgent(client=mock_anthropic_client),
        MedicalCodingAgent(client=mock_anthropic_client),
        ComplianceAgent(client=mock_anthropic_client),
        PriorAuthorizationAgent(client=mock_anthropic_client),
        QualityAssuranceAgent(client=mock_anthropic_client),
    ]

    for agent in agents:
        assert isinstance(agent, BaseAgent)
        assert hasattr(agent, "run")
        assert hasattr(agent, "_build_system_prompt")
        assert hasattr(agent, "_system_prompt")


def test_all_agents_have_unique_names(mock_anthropic_client):
    """Test all agents have distinct names."""
    agents = [
        ClinicalDocumentationAgent(client=mock_anthropic_client),
        MedicalCodingAgent(client=mock_anthropic_client),
        ComplianceAgent(client=mock_anthropic_client),
        PriorAuthorizationAgent(client=mock_anthropic_client),
        QualityAssuranceAgent(client=mock_anthropic_client),
    ]

    names = [a.agent_name for a in agents]
    assert len(names) == len(set(names)), f"Duplicate agent names: {names}"


def test_all_agents_load_skills(mock_anthropic_client):
    """Test all agents successfully load their required skills."""
    agents = [
        ClinicalDocumentationAgent(client=mock_anthropic_client),
        MedicalCodingAgent(client=mock_anthropic_client),
        ComplianceAgent(client=mock_anthropic_client),
        PriorAuthorizationAgent(client=mock_anthropic_client),
        QualityAssuranceAgent(client=mock_anthropic_client),
    ]

    for agent in agents:
        # System prompt should contain content from loaded skills
        assert len(agent._system_prompt) > 100, f"{agent.agent_name} has empty system prompt"
