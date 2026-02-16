"""
Epic FHIR Client with SMART on FHIR authentication.

Implements Epic-specific authentication and FHIR R4 operations
using the SMART on FHIR Backend Services authorization flow (JWT).
"""

import base64
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import httpx
import jwt

from src.python.fhir.base_client import BaseFHIRClient
from src.python.utils.config import settings
from src.python.utils.logging import get_logger

logger = get_logger(__name__)


class EpicFHIRClient(BaseFHIRClient):
    """
    Epic FHIR R4 client with SMART on FHIR Backend Services authentication.

    Uses JWT-based client authentication for server-to-server access.
    Supports Epic's production and sandbox FHIR servers.
    """

    def __init__(
        self,
        base_url: str | None = None,
        client_id: str | None = None,
        private_key_path: str | None = None,
        auth_url: str | None = None,
        timeout: int = 30,
    ):
        """
        Initialize Epic FHIR client.

        Args:
            base_url: Epic FHIR base URL (defaults to settings)
            client_id: Epic client ID (defaults to settings)
            private_key_path: Path to JWT private key (defaults to settings)
            auth_url: OAuth token endpoint (defaults to settings)
            timeout: Request timeout in seconds
        """
        base_url = base_url or settings.epic_fhir_base_url
        client_id = client_id or settings.epic_client_id
        self.auth_url = auth_url or settings.epic_auth_url
        self.private_key_path = private_key_path or settings.epic_private_key_path

        super().__init__(
            base_url=base_url,
            client_id=client_id,
            timeout=timeout,
        )

        logger.info(
            "epic_fhir_client_initialized",
            base_url=self.base_url,
            auth_url=self.auth_url,
            has_private_key=bool(self.private_key_path),
        )

    def _load_private_key(self) -> str:
        """
        Load private key from file.

        Returns:
            Private key content

        Raises:
            FileNotFoundError: If private key file not found
        """
        if not self.private_key_path:
            raise ValueError("Private key path not configured")

        key_path = Path(self.private_key_path)
        if not key_path.exists():
            raise FileNotFoundError(f"Private key not found: {key_path}")

        with open(key_path, "r") as f:
            private_key = f.read()

        logger.debug("epic_private_key_loaded", path=self.private_key_path)
        return private_key

    def _generate_jwt_assertion(self) -> str:
        """
        Generate JWT assertion for client authentication.

        Returns:
            Signed JWT token
        """
        private_key = self._load_private_key()

        # JWT claims for Epic backend services auth
        now = int(time.time())
        claims = {
            "iss": self.client_id,  # Issuer (client ID)
            "sub": self.client_id,  # Subject (client ID)
            "aud": self.auth_url,  # Audience (token endpoint)
            "jti": f"{self.client_id}-{now}",  # Unique JWT ID
            "exp": now + 300,  # Expires in 5 minutes
            "iat": now,  # Issued at
        }

        # Sign JWT with RS384 (Epic requirement)
        token = jwt.encode(
            claims,
            private_key,
            algorithm="RS384",
        )

        logger.debug("epic_jwt_assertion_generated", iss=self.client_id, exp=claims["exp"])
        return token

    async def authenticate(self) -> str:
        """
        Authenticate with Epic using SMART on FHIR Backend Services.

        Uses JWT-based client authentication (client_credentials grant).

        Returns:
            Access token

        Raises:
            AuthenticationError: If authentication fails
        """
        logger.info("epic_authentication_started")

        try:
            # Generate JWT assertion
            jwt_assertion = self._generate_jwt_assertion()

            # Request access token
            data = {
                "grant_type": "client_credentials",
                "client_assertion_type": "urn:ietf:params:oauth:client-assertion-type:jwt-bearer",
                "client_assertion": jwt_assertion,
            }

            response = await self.http_client.post(
                self.auth_url,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            response.raise_for_status()
            token_data = response.json()

            # Store access token
            self._access_token = token_data["access_token"]
            expires_in = token_data.get("expires_in", 3600)
            self._token_expiry = datetime.now() + timedelta(seconds=expires_in - 60)

            logger.info(
                "epic_authentication_success",
                expires_in=expires_in,
                token_type=token_data.get("token_type"),
            )

            return self._access_token

        except httpx.HTTPError as e:
            logger.error(
                "epic_authentication_failed",
                error=str(e),
                status_code=getattr(e.response, "status_code", None) if hasattr(e, "response") else None,
            )
            raise AuthenticationError(f"Epic authentication failed: {e}")
        except Exception as e:
            logger.error("epic_authentication_error", error=str(e))
            raise AuthenticationError(f"Authentication error: {e}")

    async def get_patient_everything(
        self,
        patient_id: str,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict[str, Any]:
        """
        Get comprehensive patient data using Epic's $everything operation.

        This returns a bundle with all resources related to the patient.

        Args:
            patient_id: FHIR Patient ID
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Returns:
            Bundle with all patient resources
        """
        params: dict[str, Any] = {}

        if start_date:
            params["start"] = start_date
        if end_date:
            params["end"] = end_date

        logger.info(
            "epic_fetching_patient_everything",
            patient_id=patient_id,
            start_date=start_date,
            end_date=end_date,
        )

        data = await self._make_request(
            "GET",
            f"Patient/{patient_id}/$everything",
            params=params,
        )

        logger.info("epic_patient_everything_retrieved", patient_id=patient_id)
        return data


class AuthenticationError(Exception):
    """Raised when FHIR authentication fails."""

    pass


# Convenience function for quick patient lookup
async def get_epic_patient(patient_id: str) -> dict[str, Any]:
    """
    Quick lookup of Epic patient by ID.

    Args:
        patient_id: FHIR Patient ID

    Returns:
        Patient resource as dict
    """
    async with EpicFHIRClient() as client:
        patient = await client.get_patient(patient_id)
        return patient.dict()
