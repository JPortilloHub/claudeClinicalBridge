"""
Compliance rate evaluation.

Measures the agent pipeline's ability to detect documentation gaps,
coding errors, and compliance issues against known ground truth issues
in the golden dataset.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.python.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ComplianceRateResult:
    """Result from evaluating compliance detection on a single test case."""

    case_id: str
    expected_issues: list[str]
    detected_issues: list[str]
    true_positives: list[str] = field(default_factory=list)
    false_positives: list[str] = field(default_factory=list)
    false_negatives: list[str] = field(default_factory=list)

    @property
    def detection_rate(self) -> float:
        """Proportion of expected issues that were detected (recall)."""
        if not self.expected_issues:
            return 1.0  # No issues expected, nothing to miss
        return len(self.true_positives) / len(self.expected_issues)

    @property
    def precision(self) -> float:
        if not self.detected_issues:
            return 1.0 if not self.expected_issues else 0.0
        return len(self.true_positives) / len(self.detected_issues)

    @property
    def f1_score(self) -> float:
        p, r = self.precision, self.detection_rate
        if p + r == 0:
            return 0.0
        return 2 * p * r / (p + r)

    @property
    def all_detected(self) -> bool:
        return len(self.false_negatives) == 0


@dataclass
class ComplianceRateReport:
    """Aggregated compliance detection metrics."""

    results: list[ComplianceRateResult] = field(default_factory=list)
    target_detection_rate: float = 0.95

    def add(self, result: ComplianceRateResult) -> None:
        self.results.append(result)

    @property
    def total_cases(self) -> int:
        return len(self.results)

    @property
    def all_detected_count(self) -> int:
        return sum(1 for r in self.results if r.all_detected)

    @property
    def mean_detection_rate(self) -> float:
        if not self.results:
            return 0.0
        return sum(r.detection_rate for r in self.results) / len(self.results)

    @property
    def mean_precision(self) -> float:
        if not self.results:
            return 0.0
        return sum(r.precision for r in self.results) / len(self.results)

    @property
    def mean_f1(self) -> float:
        if not self.results:
            return 0.0
        return sum(r.f1_score for r in self.results) / len(self.results)

    @property
    def meets_target(self) -> bool:
        return self.mean_detection_rate >= self.target_detection_rate

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_cases": self.total_cases,
            "all_detected_count": self.all_detected_count,
            "mean_detection_rate": round(self.mean_detection_rate, 3),
            "mean_precision": round(self.mean_precision, 3),
            "mean_f1": round(self.mean_f1, 3),
            "target_detection_rate": self.target_detection_rate,
            "meets_target": self.meets_target,
        }


def evaluate_compliance(
    case_id: str,
    expected_issues: list[str],
    detected_issues: list[str],
) -> ComplianceRateResult:
    """
    Evaluate compliance issue detection against ground truth.

    Uses keyword-based fuzzy matching: an expected issue is considered
    detected if any detected issue contains at least one significant keyword
    from the expected issue description.

    Args:
        case_id: Test case identifier
        expected_issues: Known issues from ground truth
        detected_issues: Issues detected by the pipeline

    Returns:
        ComplianceRateResult with detection metrics
    """
    # Normalize for comparison
    expected_lower = [e.lower().strip() for e in expected_issues]
    detected_lower = [d.lower().strip() for d in detected_issues]

    tp = []
    matched_detected = set()

    for expected in expected_lower:
        keywords = _extract_keywords(expected)
        for idx, detected in enumerate(detected_lower):
            if idx in matched_detected:
                continue
            if _keywords_match(keywords, detected):
                tp.append(expected)
                matched_detected.add(idx)
                break

    fn = [e for e in expected_lower if e not in tp]
    fp = [d for idx, d in enumerate(detected_lower) if idx not in matched_detected]

    result = ComplianceRateResult(
        case_id=case_id,
        expected_issues=expected_issues,
        detected_issues=detected_issues,
        true_positives=tp,
        false_positives=fp,
        false_negatives=fn,
    )

    logger.info(
        "compliance_rate_evaluated",
        case_id=case_id,
        detection_rate=round(result.detection_rate, 3),
        precision=round(result.precision, 3),
        all_detected=result.all_detected,
    )

    return result


# Stop words to exclude from keyword matching
_STOP_WORDS = frozenset({
    "a", "an", "the", "is", "are", "was", "were", "be", "been",
    "in", "on", "at", "to", "for", "of", "with", "by", "from",
    "and", "or", "not", "no", "but", "if", "has", "had", "have",
    "this", "that", "it", "its",
})


def _extract_keywords(text: str) -> list[str]:
    """Extract significant keywords from a text string."""
    words = text.lower().split()
    return [w for w in words if len(w) > 2 and w not in _STOP_WORDS]


def _keywords_match(keywords: list[str], text: str) -> bool:
    """Check if enough keywords from the expected issue appear in the detected text."""
    if not keywords:
        return False
    matched = sum(1 for kw in keywords if kw in text)
    # At least 50% of keywords must match
    return matched >= max(1, len(keywords) // 2)
