"""
Coding accuracy evaluation.

Compares agent-suggested ICD-10 and CPT codes against ground truth
from a golden dataset. Calculates exact match, top-N accuracy,
precision, recall, and F1 score.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.python.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class CodingAccuracyResult:
    """Result from evaluating a single test case."""

    case_id: str
    expected_codes: list[str]
    predicted_codes: list[str]
    true_positives: list[str] = field(default_factory=list)
    false_positives: list[str] = field(default_factory=list)
    false_negatives: list[str] = field(default_factory=list)

    @property
    def exact_match(self) -> bool:
        """Whether predicted codes exactly match expected (order-independent)."""
        return set(self.expected_codes) == set(self.predicted_codes)

    @property
    def precision(self) -> float:
        if not self.predicted_codes:
            return 0.0
        return len(self.true_positives) / len(self.predicted_codes)

    @property
    def recall(self) -> float:
        if not self.expected_codes:
            return 0.0
        return len(self.true_positives) / len(self.expected_codes)

    @property
    def f1_score(self) -> float:
        p, r = self.precision, self.recall
        if p + r == 0:
            return 0.0
        return 2 * p * r / (p + r)


@dataclass
class CodingAccuracyReport:
    """Aggregated coding accuracy metrics across all test cases."""

    results: list[CodingAccuracyResult] = field(default_factory=list)
    code_type: str = "all"
    target_accuracy: float = 0.90

    def add(self, result: CodingAccuracyResult) -> None:
        self.results.append(result)

    @property
    def total_cases(self) -> int:
        return len(self.results)

    @property
    def exact_match_count(self) -> int:
        return sum(1 for r in self.results if r.exact_match)

    @property
    def exact_match_rate(self) -> float:
        if not self.results:
            return 0.0
        return self.exact_match_count / len(self.results)

    @property
    def mean_precision(self) -> float:
        if not self.results:
            return 0.0
        return sum(r.precision for r in self.results) / len(self.results)

    @property
    def mean_recall(self) -> float:
        if not self.results:
            return 0.0
        return sum(r.recall for r in self.results) / len(self.results)

    @property
    def mean_f1(self) -> float:
        if not self.results:
            return 0.0
        return sum(r.f1_score for r in self.results) / len(self.results)

    @property
    def meets_target(self) -> bool:
        """Target: mean F1 >= target_accuracy."""
        return self.mean_f1 >= self.target_accuracy

    def to_dict(self) -> dict[str, Any]:
        return {
            "code_type": self.code_type,
            "total_cases": self.total_cases,
            "exact_match_rate": round(self.exact_match_rate, 3),
            "mean_precision": round(self.mean_precision, 3),
            "mean_recall": round(self.mean_recall, 3),
            "mean_f1": round(self.mean_f1, 3),
            "target_accuracy": self.target_accuracy,
            "meets_target": self.meets_target,
        }


def evaluate_codes(
    case_id: str,
    expected: list[str],
    predicted: list[str],
) -> CodingAccuracyResult:
    """
    Evaluate predicted codes against expected ground truth.

    Args:
        case_id: Identifier for the test case
        expected: Ground truth codes
        predicted: Agent-predicted codes

    Returns:
        CodingAccuracyResult with precision/recall/F1
    """
    expected_set = {c.strip().upper() for c in expected}
    predicted_set = {c.strip().upper() for c in predicted}

    tp = sorted(expected_set & predicted_set)
    fp = sorted(predicted_set - expected_set)
    fn = sorted(expected_set - predicted_set)

    result = CodingAccuracyResult(
        case_id=case_id,
        expected_codes=sorted(expected_set),
        predicted_codes=sorted(predicted_set),
        true_positives=tp,
        false_positives=fp,
        false_negatives=fn,
    )

    logger.info(
        "coding_accuracy_evaluated",
        case_id=case_id,
        exact_match=result.exact_match,
        precision=round(result.precision, 3),
        recall=round(result.recall, 3),
        f1=round(result.f1_score, 3),
    )

    return result
