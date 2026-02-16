"""
Unit tests for Payer Policy MCP Server and PolicyStore.
"""

import json
import sqlite3
import tempfile
from pathlib import Path

import pytest

from src.python.mcp_servers.payer_policy.policy_store import PayerPolicy, PolicyStore
from src.python.mcp_servers.payer_policy.server import (
    check_auth_requirements,
    get_documentation_requirements,
    get_policy_store,
    validate_medical_necessity,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def temp_db():
    """Create temporary SQLite database."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    yield db_path
    Path(db_path).unlink(missing_ok=True)


@pytest.fixture
def sample_policies():
    """Sample policy data for testing."""
    return [
        {
            "payer": "Medicare",
            "cpt_code": "99214",
            "procedure_name": "Office visit, established patient",
            "requires_prior_auth": False,
            "documentation_requirements": [
                "Chief complaint",
                "History of present illness",
                "Physical examination",
            ],
            "medical_necessity_criteria": [
                "Established patient",
                "Medically necessary",
            ],
            "reimbursement_rate": 131.21,
            "effective_date": "2024-01-01",
            "notes": "Common E/M code",
        },
        {
            "payer": "UnitedHealthcare",
            "cpt_code": "70553",
            "procedure_name": "MRI brain with contrast",
            "requires_prior_auth": True,
            "documentation_requirements": [
                "Clinical indication",
                "Prior imaging results",
                "Neurological findings",
            ],
            "medical_necessity_criteria": [
                "Neurological symptoms documented",
                "Conservative treatment failed",
            ],
            "prior_auth_criteria": [
                "Documented symptoms",
                "Failed conservative management",
            ],
            "reimbursement_rate": 523.18,
            "effective_date": "2024-01-01",
            "notes": "Requires prior auth",
        },
        {
            "payer": "Aetna",
            "cpt_code": "27447",
            "procedure_name": "Total knee arthroplasty",
            "requires_prior_auth": True,
            "documentation_requirements": [
                "Conservative treatment history",
                "X-ray evidence",
                "Functional limitations",
            ],
            "medical_necessity_criteria": [
                "Severe pain limiting activities",
                "Failed conservative management",
                "Radiographic evidence",
            ],
            "prior_auth_criteria": [
                "Failed 3+ months conservative treatment",
                "Grade 3 or 4 on X-ray",
            ],
            "reimbursement_rate": 1456.89,
            "effective_date": "2024-01-01",
            "notes": "Major surgery",
        },
    ]


@pytest.fixture
def sample_policies_json(tmp_path, sample_policies):
    """Create temporary JSON file with sample policies."""
    json_file = tmp_path / "test_policies.json"
    data = {"policies": sample_policies}
    with open(json_file, "w") as f:
        json.dump(data, f, indent=2)
    return str(json_file)


@pytest.fixture
def policy_store(temp_db, sample_policies_json):
    """Create PolicyStore with sample data."""
    store = PolicyStore(db_path=temp_db)
    store.load_policies_from_json(sample_policies_json)
    return store


# ============================================================================
# PolicyStore Tests
# ============================================================================


def test_policy_store_initialization(temp_db):
    """Test PolicyStore initializes database correctly."""
    store = PolicyStore(db_path=temp_db)

    # Check database exists
    assert Path(temp_db).exists()

    # Check tables exist
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='policies'"
    )
    assert cursor.fetchone() is not None
    conn.close()


def test_load_policies_from_json(policy_store):
    """Test loading policies from JSON file."""
    count = policy_store.count_policies()
    assert count == 3


def test_load_policies_invalid_json(temp_db, tmp_path):
    """Test loading from invalid JSON file."""
    store = PolicyStore(db_path=temp_db)

    # Non-existent file
    with pytest.raises(FileNotFoundError):
        store.load_policies_from_json("/nonexistent/file.json")

    # Empty policies
    empty_file = tmp_path / "empty.json"
    with open(empty_file, "w") as f:
        json.dump({"policies": []}, f)

    with pytest.raises(ValueError, match="No policies found"):
        store.load_policies_from_json(str(empty_file))


def test_get_policy_found(policy_store):
    """Test retrieving existing policy."""
    policy = policy_store.get_policy("Medicare", "99214")

    assert policy is not None
    assert isinstance(policy, PayerPolicy)
    assert policy.payer == "Medicare"
    assert policy.cpt_code == "99214"
    assert policy.procedure_name == "Office visit, established patient"
    assert policy.requires_prior_auth is False
    assert len(policy.documentation_requirements) == 3
    assert len(policy.medical_necessity_criteria) == 2


def test_get_policy_not_found(policy_store):
    """Test retrieving non-existent policy."""
    policy = policy_store.get_policy("Medicare", "99999")
    assert policy is None


def test_get_policy_with_prior_auth_criteria(policy_store):
    """Test retrieving policy with prior auth criteria."""
    policy = policy_store.get_policy("UnitedHealthcare", "70553")

    assert policy is not None
    assert policy.requires_prior_auth is True
    assert policy.prior_auth_criteria is not None
    assert len(policy.prior_auth_criteria) == 2
    assert "Documented symptoms" in policy.prior_auth_criteria


def test_search_policies_by_payer(policy_store):
    """Test searching policies by payer."""
    policies = policy_store.search_policies(payer="Medicare")

    assert len(policies) == 1
    assert policies[0].payer == "Medicare"


def test_search_policies_by_cpt_code(policy_store):
    """Test searching policies by CPT code."""
    policies = policy_store.search_policies(cpt_code="70553")

    assert len(policies) == 1
    assert policies[0].cpt_code == "70553"


def test_search_policies_by_prior_auth(policy_store):
    """Test searching policies requiring prior auth."""
    policies = policy_store.search_policies(requires_prior_auth=True)

    assert len(policies) == 2
    assert all(p.requires_prior_auth for p in policies)


def test_search_policies_multiple_filters(policy_store):
    """Test searching with multiple filters."""
    policies = policy_store.search_policies(
        payer="UnitedHealthcare",
        requires_prior_auth=True,
    )

    assert len(policies) == 1
    assert policies[0].payer == "UnitedHealthcare"
    assert policies[0].requires_prior_auth is True


def test_search_policies_limit(policy_store):
    """Test search result limit."""
    policies = policy_store.search_policies(limit=2)

    assert len(policies) == 2


def test_get_all_payers(policy_store):
    """Test retrieving all unique payers."""
    payers = policy_store.get_all_payers()

    assert len(payers) == 3
    assert "Medicare" in payers
    assert "UnitedHealthcare" in payers
    assert "Aetna" in payers


def test_count_policies(policy_store):
    """Test counting total policies."""
    count = policy_store.count_policies()
    assert count == 3


# ============================================================================
# MCP Tools Tests
# ============================================================================


@pytest.mark.asyncio
async def test_check_auth_requirements_found(policy_store, monkeypatch):
    """Test check_auth_requirements with existing policy."""
    # Mock get_policy_store to return our test store
    monkeypatch.setattr(
        "src.python.mcp_servers.payer_policy.server.get_policy_store",
        lambda: policy_store,
    )

    result = await check_auth_requirements("UnitedHealthcare", "70553")

    assert result["requires_prior_auth"] is True
    assert result["payer"] == "UnitedHealthcare"
    assert result["cpt_code"] == "70553"
    assert result["procedure_name"] == "MRI brain with contrast"
    assert len(result["prior_auth_criteria"]) == 2
    assert "error" not in result


@pytest.mark.asyncio
async def test_check_auth_requirements_not_found(policy_store, monkeypatch):
    """Test check_auth_requirements with non-existent policy."""
    monkeypatch.setattr(
        "src.python.mcp_servers.payer_policy.server.get_policy_store",
        lambda: policy_store,
    )

    result = await check_auth_requirements("Medicare", "99999")

    assert result["requires_prior_auth"] is None
    assert result["payer"] == "Medicare"
    assert result["cpt_code"] == "99999"
    assert result["procedure_name"] is None
    assert "error" in result


@pytest.mark.asyncio
async def test_check_auth_requirements_no_prior_auth(policy_store, monkeypatch):
    """Test check_auth_requirements for procedure not requiring prior auth."""
    monkeypatch.setattr(
        "src.python.mcp_servers.payer_policy.server.get_policy_store",
        lambda: policy_store,
    )

    result = await check_auth_requirements("Medicare", "99214")

    assert result["requires_prior_auth"] is False
    assert result["prior_auth_criteria"] is None
    assert "error" not in result


@pytest.mark.asyncio
async def test_get_documentation_requirements_found(policy_store, monkeypatch):
    """Test get_documentation_requirements with existing policy."""
    monkeypatch.setattr(
        "src.python.mcp_servers.payer_policy.server.get_policy_store",
        lambda: policy_store,
    )

    result = await get_documentation_requirements("Medicare", "99214")

    assert len(result["documentation_requirements"]) == 3
    assert "Chief complaint" in result["documentation_requirements"]
    assert len(result["medical_necessity_criteria"]) == 2
    assert result["payer"] == "Medicare"
    assert result["cpt_code"] == "99214"
    assert result["procedure_name"] == "Office visit, established patient"
    assert "error" not in result


@pytest.mark.asyncio
async def test_get_documentation_requirements_not_found(policy_store, monkeypatch):
    """Test get_documentation_requirements with non-existent policy."""
    monkeypatch.setattr(
        "src.python.mcp_servers.payer_policy.server.get_policy_store",
        lambda: policy_store,
    )

    result = await get_documentation_requirements("Medicare", "99999")

    assert result["documentation_requirements"] == []
    assert result["medical_necessity_criteria"] == []
    assert result["procedure_name"] is None
    assert "error" in result


@pytest.mark.asyncio
async def test_validate_medical_necessity_all_criteria_met(policy_store, monkeypatch):
    """Test validate_medical_necessity with all criteria met."""
    monkeypatch.setattr(
        "src.python.mcp_servers.payer_policy.server.get_policy_store",
        lambda: policy_store,
    )

    clinical_data = {
        "diagnoses": ["M17.11"],
        "symptoms": ["severe pain limiting daily activities"],
        "history": ["failed conservative management with PT and NSAIDs"],
        "findings": ["radiographic evidence of severe osteoarthritis"],
    }

    result = await validate_medical_necessity("Aetna", "27447", clinical_data)

    assert result["validation_status"] == "approved"
    assert len(result["criteria_met"]) == 3
    assert len(result["criteria_not_met"]) == 0
    assert result["payer"] == "Aetna"
    assert result["cpt_code"] == "27447"
    assert "error" not in result


@pytest.mark.asyncio
async def test_validate_medical_necessity_partial_criteria(policy_store, monkeypatch):
    """Test validate_medical_necessity with partial criteria met."""
    monkeypatch.setattr(
        "src.python.mcp_servers.payer_policy.server.get_policy_store",
        lambda: policy_store,
    )

    clinical_data = {
        "diagnoses": ["M17.11"],
        "symptoms": ["severe pain"],
        "history": ["failed conservative management"],
        "findings": [],  # Missing radiographic evidence
    }

    result = await validate_medical_necessity("Aetna", "27447", clinical_data)

    assert result["validation_status"] in ["needs_review", "insufficient_data"]
    assert len(result["criteria_met"]) >= 1
    assert len(result["criteria_not_met"]) >= 1
    assert result["payer"] == "Aetna"
    assert "error" not in result


@pytest.mark.asyncio
async def test_validate_medical_necessity_insufficient_data(policy_store, monkeypatch):
    """Test validate_medical_necessity with insufficient data."""
    monkeypatch.setattr(
        "src.python.mcp_servers.payer_policy.server.get_policy_store",
        lambda: policy_store,
    )

    clinical_data = {
        "diagnoses": [],
        "symptoms": [],
        "history": [],
        "findings": [],
    }

    result = await validate_medical_necessity("Aetna", "27447", clinical_data)

    assert result["validation_status"] == "insufficient_data"
    assert len(result["criteria_met"]) == 0
    assert len(result["criteria_not_met"]) == 3
    assert "error" not in result


@pytest.mark.asyncio
async def test_validate_medical_necessity_not_found(policy_store, monkeypatch):
    """Test validate_medical_necessity with non-existent policy."""
    monkeypatch.setattr(
        "src.python.mcp_servers.payer_policy.server.get_policy_store",
        lambda: policy_store,
    )

    clinical_data = {"diagnoses": [], "symptoms": [], "history": [], "findings": []}

    result = await validate_medical_necessity("Medicare", "99999", clinical_data)

    assert result["validation_status"] == "insufficient_data"
    assert result["criteria_met"] == []
    assert result["all_criteria"] == []
    assert "error" in result


@pytest.mark.asyncio
async def test_mcp_tool_error_handling(monkeypatch):
    """Test MCP tool error handling when store fails."""

    def failing_store():
        raise Exception("Database connection failed")

    monkeypatch.setattr(
        "src.python.mcp_servers.payer_policy.server.get_policy_store",
        failing_store,
    )

    # Test check_auth_requirements error
    result = await check_auth_requirements("Medicare", "99214")
    assert "error" in result
    assert result["requires_prior_auth"] is None

    # Test get_documentation_requirements error
    result = await get_documentation_requirements("Medicare", "99214")
    assert "error" in result
    assert result["documentation_requirements"] == []

    # Test validate_medical_necessity error
    result = await validate_medical_necessity("Medicare", "99214", {})
    assert "error" in result
    assert result["validation_status"] == "insufficient_data"


# ============================================================================
# Integration Tests
# ============================================================================


@pytest.mark.asyncio
async def test_end_to_end_workflow(policy_store, monkeypatch):
    """Test complete workflow: check auth → get requirements → validate."""
    monkeypatch.setattr(
        "src.python.mcp_servers.payer_policy.server.get_policy_store",
        lambda: policy_store,
    )

    # Step 1: Check if prior auth required
    auth_result = await check_auth_requirements("UnitedHealthcare", "70553")
    assert auth_result["requires_prior_auth"] is True

    # Step 2: Get documentation requirements
    doc_result = await get_documentation_requirements("UnitedHealthcare", "70553")
    assert len(doc_result["documentation_requirements"]) == 3
    assert len(doc_result["medical_necessity_criteria"]) == 2

    # Step 3: Validate medical necessity
    clinical_data = {
        "diagnoses": ["G43.909"],
        "symptoms": ["neurological symptoms documented"],
        "history": ["conservative treatment failed"],
        "findings": ["MRI indicated"],
    }
    validation_result = await validate_medical_necessity(
        "UnitedHealthcare", "70553", clinical_data
    )
    assert validation_result["validation_status"] in ["approved", "needs_review"]
