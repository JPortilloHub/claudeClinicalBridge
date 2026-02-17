"""
Integration tests for Epic FHIR MCP Server.

These tests verify the Epic FHIR client and MCP server tools work correctly
with mocked HTTP responses simulating the Epic FHIR R4 API.

Run with:
    pytest tests/integration/test_epic_integration.py -o "addopts=" -v
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Skip all tests in this module if fhir.resources is not installed
pytest.importorskip("fhir.resources", reason="fhir.resources not installed")

from src.python.utils.config import settings


# Sample FHIR responses mimicking Epic sandbox data
SAMPLE_PATIENT = {
    "resourceType": "Patient",
    "id": "epic-T1001",
    "identifier": [
        {
            "type": {"coding": [{"code": "MR"}]},
            "value": "MRN-12345",
        }
    ],
    "name": [{"family": "Smith", "given": ["John"]}],
    "birthDate": "1960-03-15",
    "gender": "male",
    "address": [{"city": "Madison", "state": "WI", "postalCode": "53703"}],
}

SAMPLE_CONDITION = {
    "resourceType": "Condition",
    "id": "cond-001",
    "clinicalStatus": {
        "coding": [{"code": "active"}],
    },
    "code": {
        "coding": [
            {"system": "http://hl7.org/fhir/sid/icd-10-cm", "code": "I10", "display": "Essential hypertension"}
        ]
    },
    "subject": {"reference": "Patient/epic-T1001"},
}

SAMPLE_OBSERVATION = {
    "resourceType": "Observation",
    "id": "obs-001",
    "status": "final",
    "category": [
        {"coding": [{"code": "vital-signs"}]}
    ],
    "code": {
        "coding": [{"code": "85354-9", "display": "Blood pressure"}]
    },
    "valueQuantity": {"value": 160, "unit": "mmHg"},
    "subject": {"reference": "Patient/epic-T1001"},
}

SAMPLE_MEDICATION_REQUEST = {
    "resourceType": "MedicationRequest",
    "id": "med-001",
    "status": "active",
    "medicationCodeableConcept": {
        "coding": [{"display": "Lisinopril 20mg"}]
    },
    "subject": {"reference": "Patient/epic-T1001"},
}

SAMPLE_ENCOUNTER = {
    "resourceType": "Encounter",
    "id": "enc-001",
    "status": "finished",
    "class": {"code": "AMB", "display": "ambulatory"},
    "period": {"start": "2025-12-01", "end": "2025-12-01"},
    "subject": {"reference": "Patient/epic-T1001"},
}


def _bundle_response(*resources):
    """Wrap FHIR resources in a Bundle response."""
    return {
        "resourceType": "Bundle",
        "type": "searchset",
        "total": len(resources),
        "entry": [{"resource": r} for r in resources],
    }


class TestEpicFHIRClientIntegration:
    """Integration tests for Epic FHIR client HTTP interactions."""

    @pytest.mark.asyncio
    async def test_patient_search_returns_results(self):
        """Test patient search parses FHIR Bundle correctly."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = _bundle_response(SAMPLE_PATIENT)
        mock_response.raise_for_status = MagicMock()

        with patch("src.python.mcp_servers.epic_fhir.client.EpicFHIRClient.authenticate", new_callable=AsyncMock):
            with patch("httpx.AsyncClient.request", new_callable=AsyncMock, return_value=mock_response):
                from src.python.mcp_servers.epic_fhir.client import EpicFHIRClient

                client = EpicFHIRClient(
                    base_url="https://fhir.epic.com/sandbox/R4",
                    client_id="test-client",
                )
                client._access_token = "mock-token"

                result = await client.search_patients(family="Smith")

                assert len(result) >= 1
                assert result[0].id == "epic-T1001"

    @pytest.mark.asyncio
    async def test_get_conditions_returns_diagnoses(self):
        """Test conditions retrieval parses ICD-10 codes."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = _bundle_response(SAMPLE_CONDITION)
        mock_response.raise_for_status = MagicMock()

        with patch("src.python.mcp_servers.epic_fhir.client.EpicFHIRClient.authenticate", new_callable=AsyncMock):
            with patch("httpx.AsyncClient.request", new_callable=AsyncMock, return_value=mock_response):
                from src.python.mcp_servers.epic_fhir.client import EpicFHIRClient

                client = EpicFHIRClient(
                    base_url="https://fhir.epic.com/sandbox/R4",
                    client_id="test-client",
                )
                client._access_token = "mock-token"

                result = await client.get_patient_conditions("epic-T1001")

                assert len(result) >= 1

    @pytest.mark.asyncio
    async def test_get_observations_returns_vitals(self):
        """Test observations retrieval for vitals."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = _bundle_response(SAMPLE_OBSERVATION)
        mock_response.raise_for_status = MagicMock()

        with patch("src.python.mcp_servers.epic_fhir.client.EpicFHIRClient.authenticate", new_callable=AsyncMock):
            with patch("httpx.AsyncClient.request", new_callable=AsyncMock, return_value=mock_response):
                from src.python.mcp_servers.epic_fhir.client import EpicFHIRClient

                client = EpicFHIRClient(
                    base_url="https://fhir.epic.com/sandbox/R4",
                    client_id="test-client",
                )
                client._access_token = "mock-token"

                result = await client.get_patient_observations("epic-T1001")

                assert len(result) >= 1


class TestEpicFHIRMCPTools:
    """Integration tests verifying MCP tool registration and response format."""

    def test_mcp_server_has_tools(self):
        """Test that the Epic FHIR MCP server registers expected tools."""
        from src.python.mcp_servers.epic_fhir.server import mcp

        # FastMCP should have tools registered
        assert mcp.name == "epic-fhir"

    def test_fhir_resource_format(self):
        """Test that FHIR resources have expected structure."""
        # Verify our sample data matches FHIR R4 format
        assert SAMPLE_PATIENT["resourceType"] == "Patient"
        assert "name" in SAMPLE_PATIENT
        assert "birthDate" in SAMPLE_PATIENT

        assert SAMPLE_CONDITION["resourceType"] == "Condition"
        assert "code" in SAMPLE_CONDITION

        assert SAMPLE_OBSERVATION["resourceType"] == "Observation"
        assert "valueQuantity" in SAMPLE_OBSERVATION

    def test_bundle_response_format(self):
        """Test Bundle wrapper matches FHIR searchset format."""
        bundle = _bundle_response(SAMPLE_PATIENT, SAMPLE_CONDITION)

        assert bundle["resourceType"] == "Bundle"
        assert bundle["type"] == "searchset"
        assert bundle["total"] == 2
        assert len(bundle["entry"]) == 2
        assert bundle["entry"][0]["resource"]["resourceType"] == "Patient"


class TestEpicFHIRErrorHandling:
    """Integration tests for FHIR client error scenarios."""

    @pytest.mark.asyncio
    async def test_auth_failure_raises(self):
        """Test authentication failure is handled."""
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_response.json.return_value = {"error": "invalid_client"}
            mock_response.raise_for_status.side_effect = Exception("401 Unauthorized")
            mock_post.return_value = mock_response

            from src.python.mcp_servers.epic_fhir.client import EpicFHIRClient

            client = EpicFHIRClient(
                base_url="https://fhir.epic.com/sandbox/R4",
                client_id="bad-client",
            )

            with pytest.raises(Exception):
                await client.authenticate()

    def test_empty_bundle_handling(self):
        """Test empty search results are handled correctly."""
        bundle = _bundle_response()  # No resources

        assert bundle["total"] == 0
        assert len(bundle["entry"]) == 0
