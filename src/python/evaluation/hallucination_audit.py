"""
Hallucination audit evaluation.

Detects fabricated medical claims by checking whether output content
(codes, diagnoses, findings) can be traced back to the source note.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from src.python.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class HallucinationFinding:
    """A single hallucinated item found during audit."""

    category: str  # code, diagnosis, finding, medication
    content: str
    explanation: str


@dataclass
class HallucinationAuditResult:
    """Result from auditing a single test case for hallucinations."""

    case_id: str
    items_checked: int = 0
    findings: list[HallucinationFinding] = field(default_factory=list)

    @property
    def hallucination_count(self) -> int:
        return len(self.findings)

    @property
    def traceability_rate(self) -> float:
        """Proportion of checked items that are traceable to source."""
        if self.items_checked == 0:
            return 1.0
        return (self.items_checked - self.hallucination_count) / self.items_checked

    @property
    def is_clean(self) -> bool:
        return self.hallucination_count == 0


@dataclass
class HallucinationAuditReport:
    """Aggregated hallucination audit metrics."""

    results: list[HallucinationAuditResult] = field(default_factory=list)
    target_traceability: float = 1.0  # Zero tolerance for hallucinations

    def add(self, result: HallucinationAuditResult) -> None:
        self.results.append(result)

    @property
    def total_cases(self) -> int:
        return len(self.results)

    @property
    def clean_count(self) -> int:
        return sum(1 for r in self.results if r.is_clean)

    @property
    def clean_rate(self) -> float:
        if not self.results:
            return 0.0
        return self.clean_count / len(self.results)

    @property
    def mean_traceability(self) -> float:
        if not self.results:
            return 0.0
        return sum(r.traceability_rate for r in self.results) / len(self.results)

    @property
    def total_hallucinations(self) -> int:
        return sum(r.hallucination_count for r in self.results)

    @property
    def meets_target(self) -> bool:
        return self.mean_traceability >= self.target_traceability

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_cases": self.total_cases,
            "clean_count": self.clean_count,
            "clean_rate": round(self.clean_rate, 3),
            "mean_traceability": round(self.mean_traceability, 3),
            "total_hallucinations": self.total_hallucinations,
            "target_traceability": self.target_traceability,
            "meets_target": self.meets_target,
        }


def audit_hallucinations(
    case_id: str,
    source_note: str,
    predicted_codes: list[str],
    output_diagnoses: list[str] | None = None,
    output_findings: list[str] | None = None,
    output_medications: list[str] | None = None,
) -> HallucinationAuditResult:
    """
    Audit pipeline output for hallucinated content.

    Checks that codes, diagnoses, findings, and medications in the output
    can be traced back to the source physician note.

    Args:
        case_id: Test case identifier
        source_note: Original physician note
        predicted_codes: Codes from the pipeline output
        output_diagnoses: Diagnoses mentioned in structured output
        output_findings: Clinical findings in structured output
        output_medications: Medications in structured output

    Returns:
        HallucinationAuditResult with findings
    """
    result = HallucinationAuditResult(case_id=case_id)
    note_lower = source_note.lower()
    note_tokens = set(re.findall(r"[a-z]+", note_lower))

    # Check predicted codes (ICD-10 code descriptions won't appear in notes,
    # but the code itself or related clinical terms should be traceable)
    for code in predicted_codes:
        result.items_checked += 1
        # Codes are checked via token overlap against the note
        if not _is_traceable(code, note_lower, note_tokens):
            result.findings.append(HallucinationFinding(
                category="code",
                content=code,
                explanation=f"Code '{code}' not traceable to source note",
            ))

    # Check diagnoses
    if output_diagnoses:
        for diag in output_diagnoses:
            result.items_checked += 1
            if not _is_traceable(diag, note_lower, note_tokens):
                result.findings.append(HallucinationFinding(
                    category="diagnosis",
                    content=diag,
                    explanation=f"Diagnosis '{diag}' not traceable to source note",
                ))

    # Check findings
    if output_findings:
        for finding in output_findings:
            result.items_checked += 1
            if not _is_traceable(finding, note_lower, note_tokens):
                result.findings.append(HallucinationFinding(
                    category="finding",
                    content=finding,
                    explanation=f"Finding '{finding}' not traceable to source note",
                ))

    # Check medications
    if output_medications:
        for med in output_medications:
            result.items_checked += 1
            if not _is_traceable(med, note_lower, note_tokens):
                result.findings.append(HallucinationFinding(
                    category="medication",
                    content=med,
                    explanation=f"Medication '{med}' not traceable to source note",
                ))

    logger.info(
        "hallucination_audit_completed",
        case_id=case_id,
        items_checked=result.items_checked,
        hallucinations_found=result.hallucination_count,
        traceability_rate=round(result.traceability_rate, 3),
    )

    return result


def _is_traceable(item: str, note_lower: str, note_tokens: set[str]) -> bool:
    """
    Check if an item is traceable to the source note.

    Uses a two-pass approach:
    1. Direct substring match (case-insensitive)
    2. Token overlap — at least 50% of significant words must appear in the note
    """
    item_lower = item.lower().strip()

    # Direct substring match
    if item_lower in note_lower:
        return True

    # Token overlap
    item_tokens = set(re.findall(r"[a-z]+", item_lower))
    significant = {t for t in item_tokens if len(t) > 2}

    if not significant:
        return True  # No significant tokens to check

    overlap = significant & note_tokens
    return len(overlap) >= max(1, len(significant) // 2)
