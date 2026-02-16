"""
Oracle Health (Cerner) FHIR Client with SMART on FHIR authentication.

Implements Oracle Health-specific authentication using JWT-based
Backend Services flow (OAuth 2.0 client_credentials grant).
"""

import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import httpx
import jwt
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization

from src.python.fhir.base_client import BaseFHIRClient
from src.python.utils.config import settings
from src.python.utils.logging import get_logger

logger = get_logger(__name__)


class AuthenticationError(Exception):
    """Raised when Oracle Health authentication fails."""

    pass


class OracleHealthFHIRClient(BaseFHIRClient):
    """
    Oracle Health (Cerner) FHIR R4 client with SMART on FHIR Backend Services authentication.

    Uses JWT-based authentication (RS384) to obtain access tokens for API requests.
    """

    def __init__(
        self,
        base_url: str | None = None,
        client_id: str | None = None,
        private_key_path: str | None = None,
        auth_url: str | None = None,
    ):
        """
        Initialize Oracle Health FHIR client.

        Args:
            base_url: Oracle Health FHIR base URL (defaults to settings)
            client_id: OAuth 2.0 client ID from Oracle Health (defaults to settings)
            private_key_path: Path to RSA private key (PEM format) for JWT signing (defaults to settings)
            auth_url: OAuth token endpoint (defaults to settings)
        """
        base_url = base_url or settings.oracle_fhir_base_url
        client_id = client_id or settings.oracle_client_id
        self.auth_url = auth_url or settings.oracle_auth_url
        self.private_key_path = private_key_path or settings.oracle_private_key_path

        super().__init__(
            base_url=base_url,
            client_id=client_id,
        )

        # Token state
        self._access_token: str | None = None
        self._token_expiry: datetime | None = None

        logger.info(
            "oracle_health_client_initialized",
            base_url=self.base_url,
            auth_url=self.auth_url,
            has_private_key=bool(self.private_key_path),
        )

    def _load_private_key(self) -> Any:
        """
        Load RSA private key from PEM file.

        Returns:
            Cryptography private key object for JWT signing

        Raises:
            FileNotFoundError: If private key file doesn't exist
        """
        key_path = Path(self.private_key_path)
        if not key_path.exists():
            raise FileNotFoundError(f"Private key not found: {self.private_key_path}")

        with open(key_path, "rb") as f:
            private_key = serialization.load_pem_private_key(
                f.read(),
                password=None,
                backend=default_backend(),
            )

        return private_key

    def _generate_jwt_assertion(self) -> str:
        """
        Generate JWT assertion for Oracle Health authentication.

        Creates a JWT signed with RS384 algorithm containing:
        - iss: client_id (issuer)
        - sub: client_id (subject)
        - aud: auth_url (audience)
        - jti: unique token ID
        - exp: expiration time (5 minutes)
        - iat: issued at time

        Returns:
            JWT assertion string

        Raises:
            FileNotFoundError: If private key file not found
        """
        private_key = self._load_private_key()

        now = int(time.time())
        claims = {
            "iss": self.client_id,
            "sub": self.client_id,
            "aud": self.auth_url,
            "jti": f"{self.client_id}-{now}",
            "exp": now + 300,  # 5 minutes
            "iat": now,
        }

        token = jwt.encode(claims, private_key, algorithm="RS384")

        logger.debug(
            "jwt_assertion_generated",
            iss=claims["iss"],
            aud=claims["aud"],
            exp=claims["exp"],
        )

        return token

    async def authenticate(self) -> str:
        """
        Authenticate with Oracle Health and obtain access token.

        Uses SMART on FHIR Backend Services flow (OAuth 2.0 client_credentials grant)
        with JWT assertion.

        Returns:
            Access token

        Raises:
            AuthenticationError: If authentication fails
        """
        try:
            jwt_assertion = self._generate_jwt_assertion()

            data = {
                "grant_type": "client_credentials",
                "client_assertion_type": "urn:ietf:params:oauth:client-assertion-type:jwt-bearer",
                "client_assertion": jwt_assertion,
            }

            logger.info("oracle_health_authentication_started", auth_url=self.auth_url)

            response = await self.http_client.post(self.auth_url, data=data)
            response.raise_for_status()

            token_data = response.json()
            self._access_token = token_data["access_token"]
            expires_in = token_data.get("expires_in", 3600)
            self._token_expiry = datetime.now() + timedelta(seconds=expires_in)

            logger.info(
                "oracle_health_authentication_success",
                expires_in=expires_in,
                token_expiry=self._token_expiry.isoformat(),
            )

            return self._access_token

        except httpx.HTTPStatusError as e:
            logger.error(
                "oracle_health_authentication_failed",
                status_code=e.response.status_code,
                error=str(e),
            )
            raise AuthenticationError(
                f"Oracle Health authentication failed: {e.response.status_code}"
            ) from e
        except Exception as e:
            logger.error("oracle_health_authentication_error", error=str(e))
            raise AuthenticationError(
                f"Oracle Health authentication error: {str(e)}"
            ) from e

    async def _ensure_authenticated(self) -> None:
        """
        Ensure client has valid access token, refreshing if needed.

        Checks token expiry and re-authenticates if token is expired
        or will expire within 60 seconds.
        """
        if self._access_token is None or self._token_expiry is None:
            await self.authenticate()
        elif datetime.now() >= self._token_expiry - timedelta(seconds=60):
            logger.info("oracle_health_token_refresh", reason="token_expiring_soon")
            await self.authenticate()

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        params: dict | None = None,
        **kwargs,
    ) -> httpx.Response:
        """
        Make authenticated FHIR API request.

        Ensures valid authentication token and adds Bearer token to headers.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: FHIR endpoint path
            params: Query parameters
            **kwargs: Additional arguments for httpx request

        Returns:
            HTTP response

        Raises:
            httpx.HTTPError: On request failure
        """
        await self._ensure_authenticated()

        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {self._access_token}"
        headers["Accept"] = "application/fhir+json"

        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        logger.debug(
            "oracle_health_api_request",
            method=method,
            endpoint=endpoint,
            params=params,
        )

        response = await self.http_client.request(
            method=method,
            url=url,
            params=params,
            headers=headers,
            **kwargs,
        )

        response.raise_for_status()
        return response
