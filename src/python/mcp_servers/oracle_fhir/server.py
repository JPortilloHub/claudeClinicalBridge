"""
Oracle Health (Cerner) FHIR MCP Server.

Provides Model Context Protocol (MCP) tools for querying Oracle Health EHR
via FHIR R4 APIs. Includes patient search, encounters, conditions, observations,
medications, and comprehensive patient data retrieval.
"""

import json
import threading
from typing import Any

from fhir.resources.bundle import Bundle
from fhir.resources.condition import Condition
from fhir.resources.encounter import Encounter
from fhir.resources.medicationrequest import MedicationRequest
from fhir.resources.observation import Observation
from fhir.resources.patient import Patient
from mcp.server.fastmcp import FastMCP

from src.python.mcp_servers.oracle_fhir.client import OracleHealthFHIRClient
from src.python.utils.logging import get_logger

logger = get_logger(__name__)

# Initialize FastMCP server
mcp = FastMCP("oracle-health-fhir")

# Global client instance (lazy initialized)
_client: OracleHealthFHIRClient | None = None
_client_lock = threading.Lock()


def get_client() -> OracleHealthFHIRClient:
    """
    Get Oracle Health FHIR client instance (lazy initialized, thread-safe).

    Returns:
        Configured Oracle Health FHIR client
    """
    global _client
    if _client is None:
        with _client_lock:
            # Double-check locking pattern
            if _client is None:
                logger.info("oracle_health_client_lazy_init")
                _client = OracleHealthFHIRClient()
    return _client


@mcp.tool()
async def search_patients(
    family: str | None = None,
    given: str | None = None,
    birthdate: str | None = None,
    identifier: str | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """
    Search for patients in Oracle Health EHR.

    Search criteria include family name, given name, birth date, and identifier.
    At least one search parameter must be provided.

    Args:
        family: Patient family (last) name
        given: Patient given (first) name
        birthdate: Patient birth date (YYYY-MM-DD format)
        identifier: Patient identifier (e.g., MRN)
        limit: Maximum number of results (default: 10, max: 50)

    Returns:
        List of patient resources with demographics

    Example:
        >>> await search_patients(family="Smith", given="John", limit=5)
        [
            {
                "id": "12345",
                "name": [{"family": "Smith", "given": ["John"]}],
                "gender": "male",
                "birthDate": "1980-01-15"
            }
        ]
    """
    client = get_client()

    # Cap limit at 50
    limit = min(limit, 50)

    logger.info(
        "oracle_search_patients",
        family=family,
        given=given,
        birthdate=birthdate,
        identifier=identifier,
        limit=limit,
    )

    try:
        patients = await client.search_patients(
            family=family,
            given=given,
            birthdate=birthdate,
            identifier=identifier,
            limit=limit,
        )

        # Convert FHIR Patient resources to dicts (Pydantic v2 compatible)
        results = []
        for patient in patients:
            if hasattr(patient, 'model_dump'):
                results.append(patient.model_dump(exclude_none=True))
            else:
                results.append(patient.dict(exclude_none=True))

        logger.info("oracle_search_patients_success", count=len(results))
        return results

    except Exception as e:
        logger.error("oracle_search_patients_error", error=str(e))
        raise


@mcp.tool()
async def get_patient(patient_id: str) -> dict[str, Any]:
    """
    Retrieve patient demographics by ID.

    Args:
        patient_id: Oracle Health patient ID

    Returns:
        Patient resource with full demographics

    Raises:
        ValueError: If patient_id is empty

    Example:
        >>> await get_patient("12345")
        {
            "id": "12345",
            "name": [{"family": "Smith", "given": ["John", "Q"]}],
            "gender": "male",
            "birthDate": "1980-01-15",
            "address": [{"city": "Springfield", "state": "IL"}]
        }
    """
    if not patient_id:
        raise ValueError("patient_id is required")

    client = get_client()

    logger.info("oracle_get_patient", patient_id=patient_id)

    try:
        patient = await client.get_patient(patient_id)

        # Convert to dict (Pydantic v2 compatible)
        if hasattr(patient, 'model_dump'):
            result = patient.model_dump(exclude_none=True)
        else:
            result = patient.dict(exclude_none=True)

        logger.info("oracle_get_patient_success", patient_id=patient_id)
        return result

    except Exception as e:
        logger.error("oracle_get_patient_error", patient_id=patient_id, error=str(e))
        raise


@mcp.tool()
async def get_patient_encounters(
    patient_id: str,
    status: str | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """
    Retrieve patient encounters (visits).

    Args:
        patient_id: Oracle Health patient ID
        status: Encounter status filter (planned, in-progress, finished, etc.)
        limit: Maximum number of results (default: 20, max: 100)

    Returns:
        List of encounter resources

    Example:
        >>> await get_patient_encounters("12345", status="finished", limit=10)
        [
            {
                "id": "enc123",
                "status": "finished",
                "class": {"code": "AMB", "display": "ambulatory"},
                "type": [{"text": "Office Visit"}],
                "period": {"start": "2024-01-15T09:00:00Z"}
            }
        ]
    """
    client = get_client()
    limit = min(limit, 100)

    logger.info(
        "oracle_get_patient_encounters",
        patient_id=patient_id,
        status=status,
        limit=limit,
    )

    try:
        encounters = await client.get_patient_encounters(
            patient_id, status=status, limit=limit
        )

        # Convert to dicts (Pydantic v2 compatible)
        results = []
        for encounter in encounters:
            if hasattr(encounter, 'model_dump'):
                results.append(encounter.model_dump(exclude_none=True))
            else:
                results.append(encounter.dict(exclude_none=True))

        logger.info(
            "oracle_get_patient_encounters_success",
            patient_id=patient_id,
            count=len(results),
        )
        return results

    except Exception as e:
        logger.error(
            "oracle_get_patient_encounters_error",
            patient_id=patient_id,
            error=str(e),
        )
        raise


@mcp.tool()
async def get_patient_conditions(
    patient_id: str,
    clinical_status: str | None = None,
    category: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """
    Retrieve patient conditions (problem list, diagnoses).

    Args:
        patient_id: Oracle Health patient ID
        clinical_status: Clinical status filter (active, resolved, etc.)
        category: Condition category (problem-list-item, encounter-diagnosis, etc.)
        limit: Maximum number of results (default: 50, max: 200)

    Returns:
        List of condition resources with diagnoses

    Example:
        >>> await get_patient_conditions("12345", clinical_status="active")
        [
            {
                "id": "cond123",
                "clinicalStatus": {"coding": [{"code": "active"}]},
                "code": {
                    "coding": [{"system": "http://hl7.org/fhir/sid/icd-10-cm", "code": "E11.9"}],
                    "text": "Type 2 diabetes mellitus"
                }
            }
        ]
    """
    client = get_client()
    limit = min(limit, 200)

    logger.info(
        "oracle_get_patient_conditions",
        patient_id=patient_id,
        clinical_status=clinical_status,
        category=category,
        limit=limit,
    )

    try:
        conditions = await client.get_patient_conditions(
            patient_id, clinical_status=clinical_status, category=category, limit=limit
        )

        # Convert to dicts (Pydantic v2 compatible)
        results = []
        for condition in conditions:
            if hasattr(condition, 'model_dump'):
                results.append(condition.model_dump(exclude_none=True))
            else:
                results.append(condition.dict(exclude_none=True))

        logger.info(
            "oracle_get_patient_conditions_success",
            patient_id=patient_id,
            count=len(results),
        )
        return results

    except Exception as e:
        logger.error(
            "oracle_get_patient_conditions_error",
            patient_id=patient_id,
            error=str(e),
        )
        raise


@mcp.tool()
async def get_patient_observations(
    patient_id: str,
    category: str | None = None,
    code: str | None = None,
    date_range: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """
    Retrieve patient observations (lab results, vitals, etc.).

    Args:
        patient_id: Oracle Health patient ID
        category: Observation category (vital-signs, laboratory, social-history, etc.)
        code: LOINC code for specific observation type
        date_range: Date range filter (e.g., "ge2024-01-01" or "ge2024-01-01&date=le2024-12-31")
        limit: Maximum number of results (default: 50, max: 200)

    Returns:
        List of observation resources with results

    Example:
        >>> await get_patient_observations("12345", category="laboratory", limit=20)
        [
            {
                "id": "obs123",
                "status": "final",
                "category": [{"coding": [{"code": "laboratory"}]}],
                "code": {"coding": [{"system": "http://loinc.org", "code": "2345-7"}]},
                "valueQuantity": {"value": 5.4, "unit": "mmol/L"}
            }
        ]
    """
    client = get_client()
    limit = min(limit, 200)

    logger.info(
        "oracle_get_patient_observations",
        patient_id=patient_id,
        category=category,
        code=code,
        date_range=date_range,
        limit=limit,
    )

    # Parse date_range into start/end for base client compatibility
    date_range_start = None
    date_range_end = None
    if date_range:
        parts = date_range.split("&date=")
        date_range_start = parts[0] if parts[0] else None
        date_range_end = parts[1] if len(parts) > 1 else None

    try:
        observations = await client.get_patient_observations(
            patient_id, category=category, code=code,
            date_range_start=date_range_start, date_range_end=date_range_end,
            limit=limit,
        )

        # Convert to dicts (Pydantic v2 compatible)
        results = []
        for observation in observations:
            if hasattr(observation, 'model_dump'):
                results.append(observation.model_dump(exclude_none=True))
            else:
                results.append(observation.dict(exclude_none=True))

        logger.info(
            "oracle_get_patient_observations_success",
            patient_id=patient_id,
            count=len(results),
        )
        return results

    except Exception as e:
        logger.error(
            "oracle_get_patient_observations_error",
            patient_id=patient_id,
            error=str(e),
        )
        raise


@mcp.tool()
async def get_patient_medications(
    patient_id: str,
    status: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """
    Retrieve patient medications (active prescriptions and medication history).

    Args:
        patient_id: Oracle Health patient ID
        status: Medication status filter (active, completed, stopped, etc.)
        limit: Maximum number of results (default: 50, max: 200)

    Returns:
        List of medication request resources

    Example:
        >>> await get_patient_medications("12345", status="active")
        [
            {
                "id": "med123",
                "status": "active",
                "medicationCodeableConcept": {
                    "coding": [{"system": "http://www.nlm.nih.gov/research/umls/rxnorm", "code": "860975"}],
                    "text": "Metformin 500mg tablet"
                },
                "dosageInstruction": [{"text": "Take 1 tablet twice daily"}]
            }
        ]
    """
    client = get_client()
    limit = min(limit, 200)

    logger.info(
        "oracle_get_patient_medications",
        patient_id=patient_id,
        status=status,
        limit=limit,
    )

    try:
        medications = await client.get_patient_medications(
            patient_id, status=status, limit=limit
        )

        # Convert to dicts (Pydantic v2 compatible)
        results = []
        for medication in medications:
            if hasattr(medication, 'model_dump'):
                results.append(medication.model_dump(exclude_none=True))
            else:
                results.append(medication.dict(exclude_none=True))

        logger.info(
            "oracle_get_patient_medications_success",
            patient_id=patient_id,
            count=len(results),
        )
        return results

    except Exception as e:
        logger.error(
            "oracle_get_patient_medications_error",
            patient_id=patient_id,
            error=str(e),
        )
        raise


@mcp.tool()
async def get_patient_everything(
    patient_id: str,
    include_encounters: bool = True,
    include_conditions: bool = True,
    include_observations: bool = True,
    include_medications: bool = True,
) -> dict[str, Any]:
    """
    Retrieve comprehensive patient data (Patient $everything operation).

    Fetches patient demographics along with selected clinical data types.
    This is a convenience tool that makes multiple API calls to gather
    related patient information.

    Args:
        patient_id: Oracle Health patient ID
        include_encounters: Include encounter history (default: True)
        include_conditions: Include problem list (default: True)
        include_observations: Include lab results and vitals (default: True)
        include_medications: Include medication list (default: True)

    Returns:
        Comprehensive patient data bundle

    Example:
        >>> await get_patient_everything("12345")
        {
            "patient": {...},
            "encounters": [...],
            "conditions": [...],
            "observations": [...],
            "medications": [...]
        }
    """
    client = get_client()

    logger.info(
        "oracle_get_patient_everything",
        patient_id=patient_id,
        include_encounters=include_encounters,
        include_conditions=include_conditions,
        include_observations=include_observations,
        include_medications=include_medications,
    )

    try:
        # Fetch patient demographics
        patient = await client.get_patient(patient_id)

        # Convert patient to dict (Pydantic v2 compatible)
        if hasattr(patient, 'model_dump'):
            patient_dict = patient.model_dump(exclude_none=True)
        else:
            patient_dict = patient.dict(exclude_none=True)

        result: dict[str, Any] = {"patient": patient_dict}

        # Fetch additional resources as requested
        if include_encounters:
            encounters = await client.get_patient_encounters(patient_id, limit=20)
            result["encounters"] = [
                enc.model_dump(exclude_none=True) if hasattr(enc, 'model_dump') else enc.dict(exclude_none=True)
                for enc in encounters
            ]

        if include_conditions:
            conditions = await client.get_patient_conditions(patient_id, limit=50)
            result["conditions"] = [
                cond.model_dump(exclude_none=True) if hasattr(cond, 'model_dump') else cond.dict(exclude_none=True)
                for cond in conditions
            ]

        if include_observations:
            observations = await client.get_patient_observations(patient_id, limit=50)
            result["observations"] = [
                obs.model_dump(exclude_none=True) if hasattr(obs, 'model_dump') else obs.dict(exclude_none=True)
                for obs in observations
            ]

        if include_medications:
            medications = await client.get_patient_medications(patient_id, limit=50)
            result["medications"] = [
                med.model_dump(exclude_none=True) if hasattr(med, 'model_dump') else med.dict(exclude_none=True)
                for med in medications
            ]

        logger.info(
            "oracle_get_patient_everything_success",
            patient_id=patient_id,
            resources_included={
                "encounters": len(result.get("encounters", [])),
                "conditions": len(result.get("conditions", [])),
                "observations": len(result.get("observations", [])),
                "medications": len(result.get("medications", [])),
            },
        )

        return result

    except Exception as e:
        logger.error(
            "oracle_get_patient_everything_error",
            patient_id=patient_id,
            error=str(e),
        )
        raise


@mcp.resource("oracle://patient/{patient_id}")
async def patient_resource(patient_id: str) -> str:
    """
    MCP resource for patient lookup.

    Provides a resource URI scheme for accessing patient data:
    oracle://patient/{patient_id}

    Args:
        patient_id: Oracle Health patient ID

    Returns:
        Patient resource as JSON string
    """
    logger.info("oracle_patient_resource", patient_id=patient_id)
    patient_data = await get_patient(patient_id)
    return json.dumps(patient_data, indent=2)
