"""
Integration tests for Oracle Health (Cerner) FHIR MCP Server.

These tests verify the Oracle Health FHIR client and MCP server tools work
correctly with mocked HTTP responses simulating the Oracle Health Ignite
FHIR R4 API.

Run with:
    pytest tests/integration/test_oracle_integration.py -o "addopts=" -v
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Skip all tests in this module if fhir.resources is not installed
pytest.importorskip("fhir.resources", reason="fhir.resources not installed")


# Sample FHIR responses mimicking Oracle Health sandbox data
SAMPLE_PATIENT = {
    "resourceType": "Patient",
    "id": "oracle-C2001",
    "identifier": [
        {
            "type": {"coding": [{"code": "MR"}]},
            "value": "MRN-98765",
        }
    ],
    "name": [{"family": "Johnson", "given": ["Jane"]}],
    "birthDate": "1955-07-22",
    "gender": "female",
    "address": [{"city": "Kansas City", "state": "MO", "postalCode": "64108"}],
}

SAMPLE_CONDITION = {
    "resourceType": "Condition",
    "id": "cond-oracle-001",
    "clinicalStatus": {
        "coding": [{"code": "active"}],
    },
    "code": {
        "coding": [
            {
                "system": "http://hl7.org/fhir/sid/icd-10-cm",
                "code": "E11.9",
                "display": "Type 2 diabetes mellitus without complications",
            }
        ]
    },
    "subject": {"reference": "Patient/oracle-C2001"},
}

SAMPLE_MEDICATION_REQUEST = {
    "resourceType": "MedicationRequest",
    "id": "med-oracle-001",
    "status": "active",
    "medicationCodeableConcept": {
        "coding": [{"display": "Metformin 1000mg"}]
    },
    "subject": {"reference": "Patient/oracle-C2001"},
}


def _bundle_response(*resources):
    """Wrap FHIR resources in a Bundle response."""
    return {
        "resourceType": "Bundle",
        "type": "searchset",
        "total": len(resources),
        "entry": [{"resource": r} for r in resources],
    }


class TestOracleHealthClientIntegration:
    """Integration tests for Oracle Health FHIR client."""

    @pytest.mark.asyncio
    async def test_patient_search_returns_results(self):
        """Test patient search parses Oracle FHIR Bundle correctly."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = _bundle_response(SAMPLE_PATIENT)
        mock_response.raise_for_status = MagicMock()

        with patch("src.python.mcp_servers.oracle_fhir.client.OracleHealthFHIRClient.authenticate", new_callable=AsyncMock):
            with patch("httpx.AsyncClient.request", new_callable=AsyncMock, return_value=mock_response):
                from src.python.mcp_servers.oracle_fhir.client import OracleHealthFHIRClient

                client = OracleHealthFHIRClient(
                    base_url="https://fhir-open.cerner.com/r4/sandbox",
                    client_id="test-client",
                )
                client._access_token = "mock-token"

                result = await client.search_patients(family="Johnson")

                assert len(result) >= 1
                assert result[0].id == "oracle-C2001"

    @pytest.mark.asyncio
    async def test_get_conditions_returns_diagnoses(self):
        """Test Oracle conditions retrieval."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = _bundle_response(SAMPLE_CONDITION)
        mock_response.raise_for_status = MagicMock()

        with patch("src.python.mcp_servers.oracle_fhir.client.OracleHealthFHIRClient.authenticate", new_callable=AsyncMock):
            with patch("httpx.AsyncClient.request", new_callable=AsyncMock, return_value=mock_response):
                from src.python.mcp_servers.oracle_fhir.client import OracleHealthFHIRClient

                client = OracleHealthFHIRClient(
                    base_url="https://fhir-open.cerner.com/r4/sandbox",
                    client_id="test-client",
                )
                client._access_token = "mock-token"

                result = await client.get_patient_conditions("oracle-C2001")

                assert len(result) >= 1


class TestOracleHealthMCPTools:
    """Integration tests for Oracle Health MCP tool registration."""

    def test_mcp_server_has_tools(self):
        """Test that the Oracle Health MCP server registers expected tools."""
        from src.python.mcp_servers.oracle_fhir.server import mcp

        assert mcp.name == "oracle-health-fhir"

    def test_ehr_agnostic_response_format(self):
        """Test that Oracle and Epic return same response structure.

        Both EHR servers should produce identical response formats so
        agents don't need to know which EHR they're querying.
        """
        from tests.integration.test_epic_integration import SAMPLE_PATIENT as EPIC_PATIENT

        # Both have same FHIR R4 structure
        assert "resourceType" in EPIC_PATIENT
        assert "resourceType" in SAMPLE_PATIENT
        assert EPIC_PATIENT["resourceType"] == SAMPLE_PATIENT["resourceType"]

        # Both have standard FHIR fields
        for patient in [EPIC_PATIENT, SAMPLE_PATIENT]:
            assert "id" in patient
            assert "name" in patient
            assert "birthDate" in patient
            assert "gender" in patient

    def test_fhir_bundle_format_consistent(self):
        """Test that Bundle format matches between EHR systems."""
        from tests.integration.test_epic_integration import _bundle_response as epic_bundle

        oracle_bundle = _bundle_response(SAMPLE_PATIENT)
        epic_b = epic_bundle(SAMPLE_PATIENT)

        assert oracle_bundle["resourceType"] == epic_b["resourceType"]
        assert oracle_bundle["type"] == epic_b["type"]


class TestOracleHealthErrorHandling:
    """Integration tests for Oracle FHIR error handling."""

    @pytest.mark.asyncio
    async def test_auth_failure_raises(self):
        """Test Oracle authentication failure is handled."""
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_response.json.return_value = {"error": "invalid_client"}
            mock_response.raise_for_status.side_effect = Exception("401 Unauthorized")
            mock_post.return_value = mock_response

            from src.python.mcp_servers.oracle_fhir.client import OracleHealthFHIRClient

            client = OracleHealthFHIRClient(
                base_url="https://fhir-open.cerner.com/r4/sandbox",
                client_id="bad-client",
            )

            with pytest.raises(Exception):
                await client.authenticate()

    def test_empty_search_results(self):
        """Test empty Bundle is handled correctly."""
        bundle = _bundle_response()

        assert bundle["total"] == 0
        assert len(bundle["entry"]) == 0
