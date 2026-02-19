"""
Base FHIR Client for interacting with FHIR R4 servers.

Provides common functionality for Epic and Oracle Health FHIR integrations,
including OAuth authentication, resource queries, and error handling.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

import httpx
from fhir.resources.bundle import Bundle
from fhir.resources.condition import Condition
from fhir.resources.encounter import Encounter
from fhir.resources.medicationrequest import MedicationRequest
from fhir.resources.observation import Observation
from fhir.resources.patient import Patient

from src.python.utils.logging import get_logger

logger = get_logger(__name__)


class BaseFHIRClient(ABC):
    """
    Base FHIR R4 client for EHR integration.

    Provides common FHIR operations that can be extended for specific EHR vendors.
    """

    def __init__(
        self,
        base_url: str,
        client_id: str | None = None,
        client_secret: str | None = None,
        timeout: int = 30,
    ):
        """
        Initialize FHIR client.

        Args:
            base_url: FHIR server base URL
            client_id: OAuth client ID
            client_secret: OAuth client secret
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.client_id = client_id
        self.client_secret = client_secret
        self.timeout = timeout

        # OAuth token storage
        self._access_token: str | None = None
        self._token_expiry: datetime | None = None

        # HTTP client
        self.http_client = httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True,
        )

        logger.info(
            "FHIR client initialized",
            base_url=self.base_url,
            has_credentials=bool(client_id and client_secret),
        )

    @abstractmethod
    async def authenticate(self) -> str:
        """
        Authenticate with FHIR server and obtain access token.

        Returns:
            Access token

        Raises:
            AuthenticationError: If authentication fails
        """
        pass

    async def _ensure_authenticated(self) -> None:
        """Ensure we have a valid access token."""
        if self._access_token is None or (
            self._token_expiry and datetime.now() >= self._token_expiry
        ):
            logger.info("Access token expired or missing, authenticating")
            await self.authenticate()

    async def _make_request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Make authenticated HTTP request to FHIR server.

        Args:
            method: HTTP method (GET, POST, PUT, etc.)
            path: API path (e.g., "Patient/123")
            params: Query parameters
            json_data: JSON body for POST/PUT

        Returns:
            Response JSON

        Raises:
            httpx.HTTPError: On request failure
        """
        await self._ensure_authenticated()

        url = f"{self.base_url}/{path.lstrip('/')}"
        headers = {
            "Authorization": f"Bearer {self._access_token}",
            "Accept": "application/fhir+json",
            "Content-Type": "application/fhir+json",
        }

        logger.debug(
            "Making FHIR request",
            method=method,
            url=url,
            params=params,
        )

        response = await self.http_client.request(
            method=method,
            url=url,
            headers=headers,
            params=params,
            json=json_data,
        )

        response.raise_for_status()
        return response.json()

    async def get_patient(self, patient_id: str) -> Patient:
        """
        Retrieve patient by ID.

        Args:
            patient_id: FHIR Patient ID

        Returns:
            Patient resource
        """
        logger.info("Fetching patient", patient_id=patient_id)

        data = await self._make_request("GET", f"Patient/{patient_id}")
        patient = Patient(**data)

        logger.info(
            "Patient retrieved",
            patient_id=patient_id,
            name=patient.name[0].text if patient.name else "Unknown",
        )

        return patient

    async def search_patients(
        self,
        family: str | None = None,
        given: str | None = None,
        birthdate: str | None = None,
        identifier: str | None = None,
        limit: int = 10,
    ) -> list[Patient]:
        """
        Search for patients.

        Args:
            family: Family (last) name
            given: Given (first) name
            birthdate: Birth date (YYYY-MM-DD)
            identifier: Patient identifier (MRN, etc.)
            limit: Maximum results

        Returns:
            List of matching patients
        """
        params: dict[str, Any] = {"_count": limit}

        if family:
            params["family"] = family
        if given:
            params["given"] = given
        if birthdate:
            params["birthdate"] = birthdate
        if identifier:
            params["identifier"] = identifier

        logger.info("Searching patients", params=params)

        data = await self._make_request("GET", "Patient", params=params)
        bundle = Bundle(**data)

        patients = []
        if bundle.entry:
            for entry in bundle.entry:
                if (
                    entry.resource
                    and getattr(entry.resource, "__resource_type__", None) == "Patient"
                ):
                    # Use model_dump() for Pydantic v2
                    resource_dict = (
                        entry.resource.model_dump()
                        if hasattr(entry.resource, "model_dump")
                        else entry.resource.dict()
                    )
                    patients.append(Patient(**resource_dict))

        logger.info("Patient search complete", num_results=len(patients))
        return patients

    async def get_patient_encounters(
        self,
        patient_id: str,
        status: str | None = None,
        limit: int = 10,
    ) -> list[Encounter]:
        """
        Get encounters for a patient.

        Args:
            patient_id: FHIR Patient ID
            status: Encounter status filter (planned, arrived, in-progress, finished)
            limit: Maximum results

        Returns:
            List of encounters
        """
        params: dict[str, Any] = {
            "patient": patient_id,
            "_count": limit,
            "_sort": "-date",
        }

        if status:
            params["status"] = status

        logger.info("Fetching patient encounters", patient_id=patient_id, status=status)

        data = await self._make_request("GET", "Encounter", params=params)
        bundle = Bundle(**data)

        encounters = []
        if bundle.entry:
            for entry in bundle.entry:
                if (
                    entry.resource
                    and getattr(entry.resource, "__resource_type__", None) == "Encounter"
                ):
                    resource_dict = (
                        entry.resource.model_dump()
                        if hasattr(entry.resource, "model_dump")
                        else entry.resource.dict()
                    )
                    encounters.append(Encounter(**resource_dict))

        logger.info(
            "Encounters retrieved",
            patient_id=patient_id,
            num_encounters=len(encounters),
        )

        return encounters

    async def get_patient_conditions(
        self,
        patient_id: str,
        clinical_status: str | None = None,
        category: str | None = None,
        limit: int = 50,
    ) -> list[Condition]:
        """
        Get conditions (diagnoses) for a patient.

        Args:
            patient_id: FHIR Patient ID
            clinical_status: Clinical status filter (active, resolved, etc.)
            category: Condition category (problem-list-item, encounter-diagnosis)
            limit: Maximum results

        Returns:
            List of conditions
        """
        params: dict[str, Any] = {
            "patient": patient_id,
            "_count": limit,
            "_sort": "-recorded-date",
        }

        if clinical_status:
            params["clinical-status"] = clinical_status
        if category:
            params["category"] = category

        logger.info("Fetching patient conditions", patient_id=patient_id)

        data = await self._make_request("GET", "Condition", params=params)
        bundle = Bundle(**data)

        conditions = []
        if bundle.entry:
            for entry in bundle.entry:
                if (
                    entry.resource
                    and getattr(entry.resource, "__resource_type__", None) == "Condition"
                ):
                    resource_dict = (
                        entry.resource.model_dump()
                        if hasattr(entry.resource, "model_dump")
                        else entry.resource.dict()
                    )
                    conditions.append(Condition(**resource_dict))

        logger.info(
            "Conditions retrieved",
            patient_id=patient_id,
            num_conditions=len(conditions),
        )

        return conditions

    async def get_patient_observations(
        self,
        patient_id: str,
        category: str | None = None,
        code: str | None = None,
        date_range_start: str | None = None,
        date_range_end: str | None = None,
        limit: int = 50,
    ) -> list[Observation]:
        """
        Get observations (labs, vitals) for a patient.

        Args:
            patient_id: FHIR Patient ID
            category: Observation category (vital-signs, laboratory, etc.)
            code: LOINC code for specific observation type
            date_range_start: Start date (YYYY-MM-DD)
            date_range_end: End date (YYYY-MM-DD)
            limit: Maximum results

        Returns:
            List of observations
        """
        params: dict[str, Any] = {
            "patient": patient_id,
            "_count": limit,
            "_sort": "-date",
        }

        if category:
            params["category"] = category
        if code:
            params["code"] = code
        if date_range_start:
            params["date"] = f"ge{date_range_start}"
        if date_range_end:
            if "date" in params:
                params["date"] = f"{params['date']}&le{date_range_end}"
            else:
                params["date"] = f"le{date_range_end}"

        logger.info("Fetching patient observations", patient_id=patient_id)

        data = await self._make_request("GET", "Observation", params=params)
        bundle = Bundle(**data)

        observations = []
        if bundle.entry:
            for entry in bundle.entry:
                if (
                    entry.resource
                    and getattr(entry.resource, "__resource_type__", None) == "Observation"
                ):
                    resource_dict = (
                        entry.resource.model_dump()
                        if hasattr(entry.resource, "model_dump")
                        else entry.resource.dict()
                    )
                    observations.append(Observation(**resource_dict))

        logger.info(
            "Observations retrieved",
            patient_id=patient_id,
            num_observations=len(observations),
        )

        return observations

    async def get_patient_medications(
        self,
        patient_id: str,
        status: str | None = None,
        limit: int = 50,
    ) -> list[MedicationRequest]:
        """
        Get medication requests for a patient.

        Args:
            patient_id: FHIR Patient ID
            status: Status filter (active, completed, stopped)
            limit: Maximum results

        Returns:
            List of medication requests
        """
        params: dict[str, Any] = {
            "patient": patient_id,
            "_count": limit,
            "_sort": "-authoredOn",
        }

        if status:
            params["status"] = status

        logger.info("Fetching patient medications", patient_id=patient_id)

        data = await self._make_request("GET", "MedicationRequest", params=params)
        bundle = Bundle(**data)

        medication_requests = []
        if bundle.entry:
            for entry in bundle.entry:
                if (
                    entry.resource
                    and getattr(entry.resource, "__resource_type__", None) == "MedicationRequest"
                ):
                    resource_dict = (
                        entry.resource.model_dump()
                        if hasattr(entry.resource, "model_dump")
                        else entry.resource.dict()
                    )
                    medication_requests.append(MedicationRequest(**resource_dict))

        logger.info(
            "Medication requests retrieved",
            patient_id=patient_id,
            num_medications=len(medication_requests),
        )

        return medication_requests

    async def close(self) -> None:
        """Close HTTP client connection."""
        await self.http_client.aclose()
        logger.info("FHIR client closed")

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
