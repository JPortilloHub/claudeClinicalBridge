"""
Clinical validity evaluation.

Checks that generated documentation and codes are clinically plausible
by validating code specificity, clinical relationships, and diagnostic
criteria alignment.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from src.python.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ValidityIssue:
    """A single clinical validity issue."""

    category: str  # specificity, relationship, plausibility, laterality
    code: str
    description: str
    severity: str  # critical, warning, info


@dataclass
class ClinicalValidityResult:
    """Result from validating a single test case."""

    case_id: str
    codes_evaluated: int = 0
    issues: list[ValidityIssue] = field(default_factory=list)
    specificity_score: float = 1.0
    laterality_score: float = 1.0
    plausibility_score: float = 1.0

    @property
    def overall_score(self) -> float:
        """Weighted average of sub-scores (0-1)."""
        return (
            self.specificity_score * 0.4
            + self.laterality_score * 0.3
            + self.plausibility_score * 0.3
        )

    @property
    def is_valid(self) -> bool:
        """No critical issues found."""
        return not any(i.severity == "critical" for i in self.issues)

    @property
    def critical_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "critical")

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "warning")


@dataclass
class ClinicalValidityReport:
    """Aggregated clinical validity metrics."""

    results: list[ClinicalValidityResult] = field(default_factory=list)
    target_validity: float = 0.95

    def add(self, result: ClinicalValidityResult) -> None:
        self.results.append(result)

    @property
    def total_cases(self) -> int:
        return len(self.results)

    @property
    def valid_count(self) -> int:
        return sum(1 for r in self.results if r.is_valid)

    @property
    def validity_rate(self) -> float:
        if not self.results:
            return 0.0
        return self.valid_count / len(self.results)

    @property
    def mean_score(self) -> float:
        if not self.results:
            return 0.0
        return sum(r.overall_score for r in self.results) / len(self.results)

    @property
    def meets_target(self) -> bool:
        return self.validity_rate >= self.target_validity

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_cases": self.total_cases,
            "valid_count": self.valid_count,
            "validity_rate": round(self.validity_rate, 3),
            "mean_score": round(self.mean_score, 3),
            "target_validity": self.target_validity,
            "meets_target": self.meets_target,
            "total_critical_issues": sum(r.critical_count for r in self.results),
            "total_warnings": sum(r.warning_count for r in self.results),
        }


# ICD-10 codes requiring laterality (musculoskeletal, injuries, etc.)
_LATERALITY_REQUIRED_PREFIXES = (
    "M1", "M2", "S", "T",  # Musculoskeletal, injuries
    "H0", "H1", "H2", "H3", "H4", "H5",  # Eye/ear
    "G5",  # Nerve
)

# Known clinically implausible code pairs (Excludes1 examples)
_CONFLICTING_PAIRS = {
    ("E10", "E11"),  # Type 1 and Type 2 diabetes
    ("I10", "I15"),  # Essential and secondary hypertension
    ("J44", "J45"),  # COPD and asthma (context-dependent but flagged)
}


def validate_clinical(
    case_id: str,
    predicted_codes: list[str],
    documentation: str = "",
) -> ClinicalValidityResult:
    """
    Validate clinical plausibility of predicted codes.

    Checks:
    1. Code specificity (enough characters for ICD-10)
    2. Laterality where required
    3. Conflicting code combinations

    Args:
        case_id: Test case identifier
        predicted_codes: List of predicted ICD-10/CPT codes
        documentation: Optional structured documentation for context

    Returns:
        ClinicalValidityResult with issues and scores
    """
    result = ClinicalValidityResult(
        case_id=case_id,
        codes_evaluated=len(predicted_codes),
    )

    if not predicted_codes:
        return result

    icd10_codes = [c for c in predicted_codes if _is_icd10(c)]
    cpt_codes = [c for c in predicted_codes if _is_cpt(c)]

    # Check specificity
    specificity_issues = _check_specificity(icd10_codes)
    result.issues.extend(specificity_issues)

    # Check laterality
    laterality_issues = _check_laterality(icd10_codes, documentation)
    result.issues.extend(laterality_issues)

    # Check conflicting codes
    conflict_issues = _check_conflicts(icd10_codes)
    result.issues.extend(conflict_issues)

    # Calculate scores
    if icd10_codes:
        spec_ok = len(icd10_codes) - len(specificity_issues)
        result.specificity_score = max(0.0, spec_ok / len(icd10_codes))

        lat_ok = len(icd10_codes) - len(laterality_issues)
        result.laterality_score = max(0.0, lat_ok / len(icd10_codes))

    result.plausibility_score = 1.0 if not conflict_issues else max(
        0.0, 1.0 - len(conflict_issues) * 0.25
    )

    logger.info(
        "clinical_validity_evaluated",
        case_id=case_id,
        codes_evaluated=len(predicted_codes),
        issues_found=len(result.issues),
        overall_score=round(result.overall_score, 3),
    )

    return result


def _is_icd10(code: str) -> bool:
    """Check if code looks like ICD-10-CM (letter + 2+ digits + optional dot section)."""
    return bool(re.match(r"^[A-Z]\d{2}", code.strip().upper()))


def _is_cpt(code: str) -> bool:
    """Check if code looks like CPT (5 digits, optional modifier)."""
    return bool(re.match(r"^\d{5}", code.strip()))


def _check_specificity(codes: list[str]) -> list[ValidityIssue]:
    """Check ICD-10 codes have sufficient specificity."""
    issues = []
    for code in codes:
        clean = code.strip().upper().replace(".", "")
        # ICD-10-CM codes should generally be 3-7 characters
        # 3-character codes are category-level and usually need more specificity
        if len(clean) <= 3:
            issues.append(ValidityIssue(
                category="specificity",
                code=code,
                description=f"Code '{code}' is category-level only — needs higher specificity",
                severity="warning",
            ))
    return issues


def _check_laterality(codes: list[str], documentation: str) -> list[ValidityIssue]:
    """Check codes requiring laterality have it specified."""
    issues = []
    for code in codes:
        clean = code.strip().upper().replace(".", "")
        needs_laterality = any(clean.startswith(p) for p in _LATERALITY_REQUIRED_PREFIXES)
        if needs_laterality and len(clean) >= 4:
            # Laterality is typically indicated by specific character positions
            # For simplicity, check if documentation mentions left/right
            doc_lower = documentation.lower()
            has_laterality_in_doc = any(
                term in doc_lower
                for term in ["left", "right", "bilateral", "unspecified"]
            )
            if not has_laterality_in_doc and documentation:
                issues.append(ValidityIssue(
                    category="laterality",
                    code=code,
                    description=f"Code '{code}' may require laterality but none found in documentation",
                    severity="warning",
                ))
    return issues


def _check_conflicts(codes: list[str]) -> list[ValidityIssue]:
    """Check for clinically implausible code combinations."""
    issues = []
    code_prefixes = [c.strip().upper().replace(".", "")[:3] for c in codes]

    for prefix_a, prefix_b in _CONFLICTING_PAIRS:
        if prefix_a in code_prefixes and prefix_b in code_prefixes:
            issues.append(ValidityIssue(
                category="plausibility",
                code=f"{prefix_a}+{prefix_b}",
                description=f"Conflicting codes: {prefix_a}* and {prefix_b}* should not appear together",
                severity="critical",
            ))

    return issues
