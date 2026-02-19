"""
Structured logging configuration using structlog.

Provides HIPAA-compliant logging with:
- Structured JSON logging for machine parsing
- PHI redaction capabilities
- Audit trail support
- Context preservation across async operations
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Any

import structlog
from structlog.dev import ConsoleRenderer
from structlog.processors import JSONRenderer
from structlog.typing import EventDict, WrappedLogger

from .config import settings


def add_app_context(logger: WrappedLogger, method_name: str, event_dict: EventDict) -> EventDict:
    """
    Add application context to all log events.

    Args:
        logger: The wrapped logger instance
        method_name: The name of the method being called
        event_dict: The event dictionary to modify

    Returns:
        Modified event dictionary with application context
    """
    event_dict["environment"] = settings.environment
    event_dict["application"] = "claude-clinical-bridge"
    return event_dict


def add_severity(logger: WrappedLogger, method_name: str, event_dict: EventDict) -> EventDict:
    """
    Add log severity level in a standardized format.

    Args:
        logger: The wrapped logger instance
        method_name: The name of the method being called
        event_dict: The event dictionary to modify

    Returns:
        Modified event dictionary with severity
    """
    if method_name == "warn":
        # Normalize 'warn' to 'warning'
        event_dict["level"] = "warning"
    else:
        event_dict["level"] = method_name
    return event_dict


def redact_phi_processor(
    logger: WrappedLogger, method_name: str, event_dict: EventDict
) -> EventDict:
    """
    Redact PHI from log events if PHI redaction is enabled.

    Args:
        logger: The wrapped logger instance
        method_name: The name of the method being called
        event_dict: The event dictionary to modify

    Returns:
        Modified event dictionary with PHI redacted
    """
    if not settings.phi_redaction_enabled:
        return event_dict

    # List of keys that might contain PHI (HIPAA 18 identifiers)
    phi_keys = [
        # Patient identifiers
        "patient_id",
        "patient_identifier",
        "pid",
        "patient",
        "patient_name",
        "name",
        "full_name",
        "first_name",
        "last_name",
        # Medical record numbers
        "mrn",
        "medical_record_number",
        "record_number",
        # Government identifiers
        "ssn",
        "social_security",
        "social_security_number",
        # Dates (except year)
        "dob",
        "date_of_birth",
        "birth_date",
        "birthdate",
        # Contact information
        "phone",
        "phone_number",
        "telephone",
        "mobile",
        "cell",
        "email",
        "email_address",
        # Geographic information
        "address",
        "street_address",
        "home_address",
        "street",
        "city",
        "zip",
        "postal_code",
        "zipcode",
        # Network/Device identifiers
        "ip_address",
        "ip",
        "device_id",
        "mac_address",
        # Account/Financial
        "account_number",
        "account",
        "certificate_number",
        "license_number",
        # Biometric
        "fingerprint",
        "voiceprint",
        "facial_image",
        # Other identifiers
        "url",
        "vehicle_identifier",
        "vin",
    ]

    for key in phi_keys:
        if key in event_dict:
            if settings.phi_redaction_method == "mask":
                event_dict[key] = "[REDACTED]"
            elif settings.phi_redaction_method == "hash":
                import hashlib

                value_hash = hashlib.sha256(str(event_dict[key]).encode()).hexdigest()[:16]
                event_dict[key] = f"[HASH:{value_hash}]"
            elif settings.phi_redaction_method == "remove":
                del event_dict[key]

    return event_dict


def setup_logging() -> None:
    """
    Configure structlog with application-specific settings.

    Sets up:
    - JSON or console rendering based on configuration
    - Log level filtering
    - File and console handlers
    - PHI redaction
    - Context preservation
    """
    # Ensure log directory exists
    log_path = Path(settings.log_file_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        level=getattr(logging, settings.log_level),
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.handlers.RotatingFileHandler(
                filename=settings.log_file_path,
                maxBytes=settings.log_file_max_bytes,
                backupCount=settings.log_file_backup_count,
            ),
        ],
    )

    # Determine renderer based on format setting
    renderer: JSONRenderer | ConsoleRenderer
    if settings.log_format == "json":
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            add_app_context,
            add_severity,
            redact_phi_processor,
            renderer,
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None, **initial_context: Any) -> structlog.stdlib.BoundLogger:
    """
    Get a configured logger instance.

    Args:
        name: Logger name (typically __name__)
        **initial_context: Initial context to bind to the logger

    Returns:
        Configured structlog logger with bound context
    """
    logger: structlog.stdlib.BoundLogger = structlog.get_logger(name)
    if initial_context:
        logger = logger.bind(**initial_context)
    return logger


# Setup logging on module import
setup_logging()


# Example usage and testing
if __name__ == "__main__":
    # Test logger
    log = get_logger(__name__)

    log.debug("Debug message", extra_field="debug_value")
    log.info("Info message", user_action="login")
    log.warning("Warning message", resource="cpu", usage=85)
    log.error("Error occurred", error_code="ERR_500", traceback="...")

    # Test PHI redaction
    log.info(
        "Patient data accessed",
        patient_id="12345",
        patient_name="John Doe",
        action="view_record",
    )

    # Test with context binding
    patient_log = get_logger(__name__, patient_id="PATIENT_123")
    patient_log.info("Accessed patient record")
    patient_log.info("Generated clinical note")
