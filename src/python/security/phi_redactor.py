"""
PHI Redactor for HIPAA compliance.

Detects and redacts the 18 HIPAA Safe Harbor identifiers from text
to prevent Protected Health Information from appearing in logs,
exports, or other non-secured outputs.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from src.python.utils.config import settings
from src.python.utils.logging import get_logger

logger = get_logger(__name__)


class RedactionMethod(Enum):
    """Method used to redact PHI."""

    MASK = "mask"       # Replace with [REDACTED]
    HASH = "hash"       # Replace with SHA-256 hash prefix
    REMOVE = "remove"   # Remove entirely


class PHICategory(Enum):
    """HIPAA Safe Harbor 18 identifier categories."""

    NAME = "name"
    DATE = "date"
    PHONE = "phone"
    EMAIL = "email"
    SSN = "ssn"
    MRN = "mrn"
    ACCOUNT_NUMBER = "account_number"
    IP_ADDRESS = "ip_address"
    URL = "url"
    AGE_OVER_89 = "age_over_89"
    ZIP_CODE = "zip_code"


@dataclass
class RedactionResult:
    """Result of a PHI redaction operation."""

    original_length: int
    redacted_length: int
    redactions: list[dict[str, str]] = field(default_factory=list)

    @property
    def redaction_count(self) -> int:
        return len(self.redactions)

    @property
    def had_phi(self) -> bool:
        return self.redaction_count > 0


# Pre-compiled regex patterns for PHI detection
_PHI_PATTERNS: list[tuple[PHICategory, re.Pattern[str]]] = [
    # SSN: 123-45-6789 or 123456789
    (PHICategory.SSN, re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    (PHICategory.SSN, re.compile(r"\b\d{9}\b(?!\d)")),

    # Phone: (123) 456-7890, 123-456-7890, 123.456.7890
    (PHICategory.PHONE, re.compile(r"\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}\b")),

    # Email
    (PHICategory.EMAIL, re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")),

    # IP Address (v4)
    (PHICategory.IP_ADDRESS, re.compile(
        r"\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\b"
    )),

    # MRN patterns: MRN-12345, MRN: 12345, MRN#12345
    (PHICategory.MRN, re.compile(r"\bMRN[#:\s-]*\d{4,10}\b", re.IGNORECASE)),

    # Account numbers: ACCT-12345, Account: 12345
    (PHICategory.ACCOUNT_NUMBER, re.compile(r"\b(?:ACCT|Account)[#:\s-]*\d{4,12}\b", re.IGNORECASE)),

    # Dates: MM/DD/YYYY, MM-DD-YYYY, YYYY-MM-DD, Month DD YYYY
    (PHICategory.DATE, re.compile(
        r"\b(?:0[1-9]|1[0-2])[/-](?:0[1-9]|[12]\d|3[01])[/-](?:19|20)\d{2}\b"
    )),
    (PHICategory.DATE, re.compile(
        r"\b(?:19|20)\d{2}[/-](?:0[1-9]|1[0-2])[/-](?:0[1-9]|[12]\d|3[01])\b"
    )),
    (PHICategory.DATE, re.compile(
        r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)"
        r"\s+\d{1,2},?\s+(?:19|20)\d{2}\b",
        re.IGNORECASE,
    )),

    # Age over 89
    (PHICategory.AGE_OVER_89, re.compile(r"\b(?:9\d|[1-9]\d{2,})[\s-]*(?:y/?o|year|yr)\b", re.IGNORECASE)),

    # ZIP code (requires "ZIP" or "zip code" prefix to avoid false positives on bare 5-digit numbers)
    (PHICategory.ZIP_CODE, re.compile(r"\b(?:ZIP|zip\s*code)[#:\s-]*\d{5}(?:-\d{4})?\b", re.IGNORECASE)),

    # URL/web addresses
    (PHICategory.URL, re.compile(r"https?://[^\s<>\"]+", re.IGNORECASE)),
]


def redact_phi(
    text: str,
    method: RedactionMethod | None = None,
    categories: set[PHICategory] | None = None,
) -> tuple[str, RedactionResult]:
    """
    Detect and redact PHI from text.

    Args:
        text: Input text potentially containing PHI
        method: Redaction method (defaults to settings.phi_redaction_method)
        categories: Optional subset of PHI categories to check (defaults to all)

    Returns:
        Tuple of (redacted_text, RedactionResult)
    """
    if method is None:
        method = RedactionMethod(settings.phi_redaction_method)

    result = RedactionResult(original_length=len(text), redacted_length=0)
    redacted = text

    for category, pattern in _PHI_PATTERNS:
        if categories and category not in categories:
            continue

        matches = list(pattern.finditer(redacted))
        if not matches:
            continue

        # Process matches in reverse order to preserve positions
        for match in reversed(matches):
            original_value = match.group()
            replacement = _get_replacement(original_value, category, method)

            result.redactions.append({
                "category": category.value,
                "replacement": replacement,
            })

            redacted = redacted[:match.start()] + replacement + redacted[match.end():]

    result.redacted_length = len(redacted)

    if result.had_phi:
        logger.info(
            "phi_redacted",
            redaction_count=result.redaction_count,
            categories=list({r["category"] for r in result.redactions}),
        )

    return redacted, result


def _get_replacement(value: str, category: PHICategory, method: RedactionMethod) -> str:
    """Generate a replacement string based on the redaction method."""
    if method == RedactionMethod.MASK:
        return f"[{category.value.upper()}]"

    if method == RedactionMethod.HASH:
        import hashlib
        hash_val = hashlib.sha256(value.encode()).hexdigest()[:8]
        return f"[{category.value.upper()}:{hash_val}]"

    if method == RedactionMethod.REMOVE:
        return ""

    return f"[{category.value.upper()}]"


def contains_phi(text: str) -> bool:
    """
    Quick check if text contains any detectable PHI.

    More efficient than full redaction when you only need a boolean check.
    """
    for _category, pattern in _PHI_PATTERNS:
        if pattern.search(text):
            return True
    return False


def redact_dict(
    data: dict[str, Any],
    method: RedactionMethod | None = None,
) -> dict[str, Any]:
    """
    Recursively redact PHI from all string values in a dictionary.

    Args:
        data: Dictionary potentially containing PHI in string values
        method: Redaction method

    Returns:
        New dictionary with PHI redacted from all string values
    """
    redacted = {}
    for key, value in data.items():
        if isinstance(value, str):
            redacted[key], _ = redact_phi(value, method)
        elif isinstance(value, dict):
            redacted[key] = redact_dict(value, method)
        elif isinstance(value, list):
            redacted[key] = [
                redact_phi(item, method)[0] if isinstance(item, str) else item
                for item in value
            ]
        else:
            redacted[key] = value
    return redacted
