"""Evaluation framework for the clinical documentation pipeline."""

from src.python.evaluation.clinical_validity import (
    ClinicalValidityReport,
    ClinicalValidityResult,
    validate_clinical,
)
from src.python.evaluation.coding_accuracy import (
    CodingAccuracyReport,
    CodingAccuracyResult,
    evaluate_codes,
)
from src.python.evaluation.compliance_rate import (
    ComplianceRateReport,
    ComplianceRateResult,
    evaluate_compliance,
)
from src.python.evaluation.hallucination_audit import (
    HallucinationAuditReport,
    HallucinationAuditResult,
    audit_hallucinations,
)
from src.python.evaluation.latency_tracker import (
    LatencyReport,
    TimingRecord,
    track_latency,
)

__all__ = [
    "ClinicalValidityReport",
    "ClinicalValidityResult",
    "CodingAccuracyReport",
    "CodingAccuracyResult",
    "ComplianceRateReport",
    "ComplianceRateResult",
    "HallucinationAuditReport",
    "HallucinationAuditResult",
    "LatencyReport",
    "TimingRecord",
    "audit_hallucinations",
    "evaluate_codes",
    "evaluate_compliance",
    "track_latency",
    "validate_clinical",
]
