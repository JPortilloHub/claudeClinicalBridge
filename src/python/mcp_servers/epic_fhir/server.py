"""
Epic FHIR MCP Server.

Provides MCP tools for querying Epic FHIR server, enabling LLM agents
to retrieve patient data, encounters, conditions, observations, and medications.

Tools:
- search_patients: Search for patients by name, DOB, or identifier
- get_patient: Get patient demographics
- get_patient_encounters: Get patient encounters
- get_patient_conditions: Get patient diagnoses
- get_patient_observations: Get labs and vitals
- get_patient_medications: Get medication orders
- get_patient_everything: Get comprehensive patient data

Resources:
- epic://patient/{patient_id}: Patient resource lookup
"""

import threading
from typing import Any

from mcp.server.fastmcp import FastMCP

from src.python.utils.logging import get_logger

from .client import EpicFHIRClient

logger = get_logger(__name__)

# Initialize FastMCP server
mcp = FastMCP("epic-fhir")

# Initialize client (lazy loading with thread safety)
_client: EpicFHIRClient | None = None
_client_lock = threading.Lock()


def get_client() -> EpicFHIRClient:
    """Get or create Epic FHIR client instance (lazy initialization, thread-safe)."""
    global _client
    if _client is None:
        with _client_lock:
            if _client is None:
                logger.info("Initializing Epic FHIR client")
                _client = EpicFHIRClient()
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
    Search for patients in Epic FHIR.

    Search by name, birth date, or identifier (MRN).
    Returns patient demographics and identifiers.

    Args:
        family: Family (last) name
        given: Given (first) name
        birthdate: Birth date in YYYY-MM-DD format
        identifier: Patient identifier (MRN)
        limit: Maximum number of results (default: 10, max: 50)

    Returns:
        List of matching patients with demographics:
        - id: FHIR Patient ID
        - identifier: Medical Record Numbers
        - name: Patient name
        - birthDate: Date of birth
        - gender: Gender
        - address: Contact information

    Example:
        >>> search_patients(family="Smith", given="John", limit=5)
        [
            {
                "id": "e.abc123",
                "name": "John Smith",
                "birthDate": "1980-01-15",
                "gender": "male",
                ...
            }
        ]
    """
    # Validate parameters
    if limit < 1:
        limit = 1
    elif limit > 50:
        logger.warning("Limit capped at 50", requested_limit=limit)
        limit = 50

    if not any([family, given, birthdate, identifier]):
        logger.warning("No search criteria provided")
        return []

    logger.info(
        "Patient search request",
        family=family,
        given=given,
        birthdate=birthdate,
        identifier=identifier,
    )

    try:
        client = get_client()
        patients = await client.search_patients(
            family=family,
            given=given,
            birthdate=birthdate,
            identifier=identifier,
            limit=limit,
        )

        # Convert to dict for MCP response (use model_dump for Pydantic v2)
        results = []
        for patient in patients:
            if hasattr(patient, "model_dump"):
                results.append(patient.model_dump(exclude_none=True))
            else:
                results.append(patient.dict(exclude_none=True))

        logger.info("Patient search completed", num_results=len(results))
        return results

    except Exception as e:
        logger.error("Patient search failed", error=str(e))
        raise


@mcp.tool()
async def get_patient(patient_id: str) -> dict[str, Any]:
    """
    Get patient demographics by FHIR ID.

    Retrieves complete patient demographics including identifiers,
    contact information, and emergency contacts.

    Args:
        patient_id: FHIR Patient ID (e.g., "e.abc123")

    Returns:
        Patient resource with full demographics:
        - id: FHIR Patient ID
        - identifier: Medical Record Numbers
        - name: Patient name(s)
        - birthDate: Date of birth
        - gender: Gender
        - address: Addresses
        - telecom: Contact information
        - maritalStatus: Marital status
        - communication: Preferred language

    Example:
        >>> get_patient("e.abc123")
        {
            "id": "e.abc123",
            "name": [{"family": "Smith", "given": ["John"]}],
            "birthDate": "1980-01-15",
            ...
        }
    """
    if not patient_id or not patient_id.strip():
        logger.warning("Empty patient_id provided")
        raise ValueError("patient_id is required")

    logger.info("Get patient request", patient_id=patient_id)

    try:
        client = get_client()
        patient = await client.get_patient(patient_id)

        # Use model_dump for Pydantic v2
        if hasattr(patient, "model_dump"):
            result = patient.model_dump(exclude_none=True)
        else:
            result = patient.dict(exclude_none=True)

        logger.info("Patient retrieved", patient_id=patient_id)
        return result

    except Exception as e:
        logger.error("Get patient failed", patient_id=patient_id, error=str(e))
        raise


@mcp.tool()
async def get_patient_encounters(
    patient_id: str,
    status: str | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """
    Get patient encounters (visits) from Epic.

    Retrieves hospital visits, clinic appointments, and other encounters.

    Args:
        patient_id: FHIR Patient ID
        status: Filter by status - "planned", "arrived", "in-progress", "finished"
        limit: Maximum results (default: 10, max: 50)

    Returns:
        List of encounters with details:
        - id: Encounter ID
        - status: Current status
        - class: Encounter type (inpatient, outpatient, emergency)
        - type: Specific encounter type codes
        - period: Start and end times
        - serviceProvider: Healthcare facility
        - diagnosis: Associated diagnoses

    Example:
        >>> get_patient_encounters("e.abc123", status="finished", limit=5)
        [
            {
                "id": "enc123",
                "status": "finished",
                "class": {"code": "AMB", "display": "ambulatory"},
                "period": {"start": "2024-01-15T09:00:00Z"},
                ...
            }
        ]
    """
    if not patient_id or not patient_id.strip():
        raise ValueError("patient_id is required")

    if limit < 1:
        limit = 1
    elif limit > 50:
        limit = 50

    logger.info(
        "Get patient encounters request",
        patient_id=patient_id,
        status=status,
    )

    try:
        client = get_client()
        encounters = await client.get_patient_encounters(
            patient_id=patient_id,
            status=status,
            limit=limit,
        )

        # Use model_dump for Pydantic v2
        results = []
        for enc in encounters:
            if hasattr(enc, "model_dump"):
                results.append(enc.model_dump(exclude_none=True))
            else:
                results.append(enc.dict(exclude_none=True))

        logger.info(
            "Patient encounters retrieved",
            patient_id=patient_id,
            num_encounters=len(results),
        )
        return results

    except Exception as e:
        logger.error(
            "Get patient encounters failed",
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
    Get patient conditions (diagnoses) from Epic.

    Retrieves problem list items, encounter diagnoses, and other conditions.

    Args:
        patient_id: FHIR Patient ID
        clinical_status: Filter by clinical status - "active", "resolved", "inactive"
        category: Filter by category - "problem-list-item", "encounter-diagnosis"
        limit: Maximum results (default: 50, max: 100)

    Returns:
        List of conditions with details:
        - id: Condition ID
        - clinicalStatus: Active, resolved, etc.
        - verificationStatus: Confirmed, provisional, etc.
        - category: Condition category
        - code: Diagnosis code (ICD-10, SNOMED CT)
        - onsetDateTime: When condition started
        - recordedDate: When recorded in system

    Example:
        >>> get_patient_conditions("e.abc123", clinical_status="active")
        [
            {
                "id": "cond123",
                "clinicalStatus": {"text": "Active"},
                "code": {
                    "coding": [{"system": "ICD-10", "code": "E11.9"}],
                    "text": "Type 2 diabetes mellitus"
                },
                ...
            }
        ]
    """
    if not patient_id or not patient_id.strip():
        raise ValueError("patient_id is required")

    if limit < 1:
        limit = 1
    elif limit > 100:
        limit = 100

    logger.info(
        "Get patient conditions request",
        patient_id=patient_id,
        clinical_status=clinical_status,
    )

    try:
        client = get_client()
        conditions = await client.get_patient_conditions(
            patient_id=patient_id,
            clinical_status=clinical_status,
            category=category,
            limit=limit,
        )

        # Use model_dump for Pydantic v2
        results = []
        for cond in conditions:
            if hasattr(cond, "model_dump"):
                results.append(cond.model_dump(exclude_none=True))
            else:
                results.append(cond.dict(exclude_none=True))

        logger.info(
            "Patient conditions retrieved",
            patient_id=patient_id,
            num_conditions=len(results),
        )
        return results

    except Exception as e:
        logger.error(
            "Get patient conditions failed",
            patient_id=patient_id,
            error=str(e),
        )
        raise


@mcp.tool()
async def get_patient_observations(
    patient_id: str,
    category: str | None = None,
    code: str | None = None,
    date_range_start: str | None = None,
    date_range_end: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """
    Get patient observations (labs, vitals) from Epic.

    Retrieves laboratory results, vital signs, and other observations.

    Args:
        patient_id: FHIR Patient ID
        category: Filter by category - "vital-signs", "laboratory", "social-history"
        code: LOINC code for specific observation (e.g., "2339-0" for glucose)
        date_range_start: Start date YYYY-MM-DD
        date_range_end: End date YYYY-MM-DD
        limit: Maximum results (default: 50, max: 100)

    Returns:
        List of observations with details:
        - id: Observation ID
        - status: final, preliminary, etc.
        - category: Observation category
        - code: LOINC code and display name
        - effectiveDateTime: When observation made
        - valueQuantity: Numeric value with unit
        - interpretation: Normal, high, low, etc.

    Example:
        >>> get_patient_observations("e.abc123", category="laboratory", limit=10)
        [
            {
                "id": "obs123",
                "status": "final",
                "code": {"text": "Glucose"},
                "valueQuantity": {"value": 95, "unit": "mg/dL"},
                ...
            }
        ]
    """
    if not patient_id or not patient_id.strip():
        raise ValueError("patient_id is required")

    if limit < 1:
        limit = 1
    elif limit > 100:
        limit = 100

    logger.info(
        "Get patient observations request",
        patient_id=patient_id,
        category=category,
    )

    try:
        client = get_client()
        observations = await client.get_patient_observations(
            patient_id=patient_id,
            category=category,
            code=code,
            date_range_start=date_range_start,
            date_range_end=date_range_end,
            limit=limit,
        )

        # Use model_dump for Pydantic v2
        results = []
        for obs in observations:
            if hasattr(obs, "model_dump"):
                results.append(obs.model_dump(exclude_none=True))
            else:
                results.append(obs.dict(exclude_none=True))

        logger.info(
            "Patient observations retrieved",
            patient_id=patient_id,
            num_observations=len(results),
        )
        return results

    except Exception as e:
        logger.error(
            "Get patient observations failed",
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
    Get patient medications from Epic.

    Retrieves active medications, medication history, and prescriptions.

    Args:
        patient_id: FHIR Patient ID
        status: Filter by status - "active", "completed", "stopped"
        limit: Maximum results (default: 50, max: 100)

    Returns:
        List of medication requests with details:
        - id: MedicationRequest ID
        - status: Current status
        - intent: order, plan, etc.
        - medicationCodeableConcept: Medication name and code
        - dosageInstruction: How to take medication
        - authoredOn: When prescribed

    Example:
        >>> get_patient_medications("e.abc123", status="active")
        [
            {
                "id": "medr123",
                "status": "active",
                "medicationCodeableConcept": {
                    "text": "Metformin 500 MG Oral Tablet"
                },
                "dosageInstruction": [{
                    "text": "Take 1 tablet twice daily"
                }],
                ...
            }
        ]
    """
    if not patient_id or not patient_id.strip():
        raise ValueError("patient_id is required")

    if limit < 1:
        limit = 1
    elif limit > 100:
        limit = 100

    logger.info(
        "Get patient medications request",
        patient_id=patient_id,
        status=status,
    )

    try:
        client = get_client()
        medications = await client.get_patient_medications(
            patient_id=patient_id,
            status=status,
            limit=limit,
        )

        # Use model_dump for Pydantic v2
        results = []
        for med in medications:
            if hasattr(med, "model_dump"):
                results.append(med.model_dump(exclude_none=True))
            else:
                results.append(med.dict(exclude_none=True))

        logger.info(
            "Patient medications retrieved",
            patient_id=patient_id,
            num_medications=len(results),
        )
        return results

    except Exception as e:
        logger.error(
            "Get patient medications failed",
            patient_id=patient_id,
            error=str(e),
        )
        raise


@mcp.tool()
async def get_patient_everything(
    patient_id: str,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict[str, Any]:
    """
    Get comprehensive patient data using Epic's $everything operation.

    Returns a FHIR Bundle containing all resources related to the patient:
    demographics, encounters, conditions, observations, medications, and more.

    This is useful for getting a complete patient chart in one call.

    Args:
        patient_id: FHIR Patient ID
        start_date: Filter resources after this date (YYYY-MM-DD)
        end_date: Filter resources before this date (YYYY-MM-DD)

    Returns:
        FHIR Bundle with all patient resources:
        - resourceType: "Bundle"
        - type: "searchset"
        - entry: List of all patient resources

    Example:
        >>> get_patient_everything("e.abc123", start_date="2024-01-01")
        {
            "resourceType": "Bundle",
            "type": "searchset",
            "entry": [
                {"resource": {"resourceType": "Patient", ...}},
                {"resource": {"resourceType": "Encounter", ...}},
                ...
            ]
        }
    """
    if not patient_id or not patient_id.strip():
        raise ValueError("patient_id is required")

    logger.info(
        "Get patient everything request",
        patient_id=patient_id,
        start_date=start_date,
        end_date=end_date,
    )

    try:
        client = get_client()
        bundle = await client.get_patient_everything(
            patient_id=patient_id,
            start_date=start_date,
            end_date=end_date,
        )

        logger.info("Patient everything retrieved", patient_id=patient_id)
        return bundle

    except Exception as e:
        logger.error(
            "Get patient everything failed",
            patient_id=patient_id,
            error=str(e),
        )
        raise


@mcp.resource("epic://patient/{patient_id}")
async def patient_resource(patient_id: str) -> str:
    """
    MCP resource for patient lookup.

    Provides a resource URI pattern for accessing Epic patients:
    - epic://patient/e.abc123

    Args:
        patient_id: FHIR Patient ID

    Returns:
        Formatted patient demographics
    """
    logger.info("Patient resource request", patient_id=patient_id)

    try:
        patient_data = await get_patient(patient_id)

        # Format as readable text
        name = "Unknown"
        if patient_data.get("name"):
            name_obj = patient_data["name"][0]
            given = " ".join(name_obj.get("given", []))
            family = name_obj.get("family", "")
            name = f"{given} {family}".strip()

        lines = [
            f"Patient: {name}",
            f"ID: {patient_data.get('id')}",
            f"Birth Date: {patient_data.get('birthDate', 'N/A')}",
            f"Gender: {patient_data.get('gender', 'N/A')}",
        ]

        if patient_data.get("identifier"):
            mrns = [
                ident.get("value") for ident in patient_data["identifier"] if ident.get("value")
            ]
            if mrns:
                lines.append(f"MRN: {', '.join(mrns[:3])}")

        return "\n".join(lines)

    except Exception as e:
        return f"Error retrieving patient {patient_id}: {e}"


# Server lifecycle hooks
# Note: FastMCP handles initialization automatically
# Client is lazily initialized on first use via get_client()


# Run server
if __name__ == "__main__":
    import asyncio

    logger.info("Starting Epic FHIR MCP Server")

    try:
        asyncio.run(mcp.run())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error("Server error", error=str(e))
        raise
