"""
Unit tests for the evaluation framework.

Tests cover:
- Latency tracking (context manager, report aggregation, percentiles)
- Coding accuracy (exact match, precision, recall, F1)
- Clinical validity (specificity, laterality, conflict detection)
- Compliance rate (keyword matching, detection rates)
- Hallucination audit (traceability, token overlap)
"""

import time

from src.python.evaluation.clinical_validity import (
    ClinicalValidityReport,
    validate_clinical,
)
from src.python.evaluation.coding_accuracy import (
    CodingAccuracyReport,
    evaluate_codes,
)
from src.python.evaluation.compliance_rate import (
    ComplianceRateReport,
    evaluate_compliance,
)
from src.python.evaluation.hallucination_audit import (
    HallucinationAuditReport,
    audit_hallucinations,
)
from src.python.evaluation.latency_tracker import LatencyReport, TimingRecord, track_latency


# ============================================================================
# Latency Tracker Tests
# ============================================================================


def test_timing_record_duration():
    """Test TimingRecord calculates duration."""
    record = TimingRecord(name="test", started_at=10.0, completed_at=12.5)
    assert record.duration_seconds == 2.5


def test_track_latency_context_manager():
    """Test track_latency measures execution time."""
    with track_latency("test_op") as record:
        time.sleep(0.01)

    assert record.duration_seconds >= 0.01
    assert record.name == "test_op"


def test_track_latency_adds_to_report():
    """Test track_latency auto-adds to report."""
    report = LatencyReport()

    with track_latency("op1", report):
        pass
    with track_latency("op2", report):
        pass

    assert report.total_records == 2


def test_latency_report_statistics():
    """Test LatencyReport statistical calculations."""
    report = LatencyReport(target_seconds=5.0)
    report.add(TimingRecord(name="a", started_at=0, completed_at=1))
    report.add(TimingRecord(name="b", started_at=0, completed_at=3))
    report.add(TimingRecord(name="c", started_at=0, completed_at=2))

    assert report.mean_seconds == 2.0
    assert report.median_seconds == 2.0
    assert report.min_seconds == 1.0
    assert report.max_seconds == 3.0
    assert report.within_target_count == 3
    assert report.within_target_rate == 1.0
    assert report.meets_target is True


def test_latency_report_p90():
    """Test p90 percentile calculation."""
    report = LatencyReport(target_seconds=10.0)
    # Add 10 records: 1, 2, 3, ..., 10
    for i in range(1, 11):
        report.add(TimingRecord(name=f"r{i}", started_at=0, completed_at=float(i)))

    # idx = int(10 * 0.9) = 9 → sorted_d[9] = 10.0
    assert report.p90_seconds == 10.0


def test_latency_report_empty():
    """Test empty report returns zero values."""
    report = LatencyReport()

    assert report.mean_seconds == 0.0
    assert report.median_seconds == 0.0
    assert report.p90_seconds == 0.0


def test_latency_report_to_dict():
    """Test report serialization."""
    report = LatencyReport(target_seconds=5.0)
    report.add(TimingRecord(name="a", started_at=0, completed_at=2))

    d = report.to_dict()
    assert d["total_records"] == 1
    assert d["mean_seconds"] == 2.0
    assert d["meets_target"] is True


# ============================================================================
# Coding Accuracy Tests
# ============================================================================


def test_evaluate_codes_exact_match():
    """Test exact match when predicted equals expected."""
    result = evaluate_codes("test-1", ["I10", "E11.42"], ["I10", "E11.42"])

    assert result.exact_match is True
    assert result.precision == 1.0
    assert result.recall == 1.0
    assert result.f1_score == 1.0


def test_evaluate_codes_partial_match():
    """Test partial match with some correct codes."""
    result = evaluate_codes("test-2", ["I10", "E11.42", "M54.5"], ["I10", "E11.42"])

    assert result.exact_match is False
    assert result.precision == 1.0  # All predicted are correct
    assert result.recall == 2 / 3  # Missed M54.5
    assert len(result.true_positives) == 2
    assert len(result.false_negatives) == 1


def test_evaluate_codes_no_match():
    """Test no match between predicted and expected."""
    result = evaluate_codes("test-3", ["I10"], ["E11.42"])

    assert result.exact_match is False
    assert result.precision == 0.0
    assert result.recall == 0.0
    assert result.f1_score == 0.0


def test_evaluate_codes_case_insensitive():
    """Test code comparison is case-insensitive."""
    result = evaluate_codes("test-4", ["i10", "e11.42"], ["I10", "E11.42"])

    assert result.exact_match is True


def test_evaluate_codes_empty_predicted():
    """Test with no predicted codes."""
    result = evaluate_codes("test-5", ["I10"], [])

    assert result.precision == 0.0
    assert result.recall == 0.0


def test_coding_accuracy_report():
    """Test aggregated coding accuracy report."""
    report = CodingAccuracyReport(target_accuracy=0.8)

    report.add(evaluate_codes("c1", ["I10"], ["I10"]))
    report.add(evaluate_codes("c2", ["I10", "E11.42"], ["I10"]))

    assert report.total_cases == 2
    assert report.exact_match_count == 1
    assert report.exact_match_rate == 0.5
    assert report.mean_precision == 1.0
    assert report.mean_recall == 0.75  # (1.0 + 0.5) / 2
    assert report.meets_target is True  # mean_f1 should be > 0.8


def test_coding_accuracy_report_to_dict():
    """Test report serialization."""
    report = CodingAccuracyReport(code_type="icd10")
    report.add(evaluate_codes("c1", ["I10"], ["I10"]))

    d = report.to_dict()
    assert d["code_type"] == "icd10"
    assert d["mean_f1"] == 1.0


# ============================================================================
# Clinical Validity Tests
# ============================================================================


def test_validate_clinical_valid_codes():
    """Test validation of clinically valid codes."""
    result = validate_clinical(
        "cv-1",
        ["I10", "E11.42"],
        "Patient with essential hypertension and type 2 diabetes, right foot numbness",
    )

    assert result.is_valid is True
    assert result.overall_score > 0.5


def test_validate_clinical_specificity_warning():
    """Test category-level code triggers specificity warning."""
    result = validate_clinical(
        "cv-2",
        ["I10"],  # 3-char code
        "Hypertension",
    )

    specificity_issues = [i for i in result.issues if i.category == "specificity"]
    assert len(specificity_issues) == 1


def test_validate_clinical_conflicting_codes():
    """Test conflicting codes are detected."""
    result = validate_clinical(
        "cv-3",
        ["E10.9", "E11.9"],  # Type 1 + Type 2 diabetes
        "Patient has diabetes",
    )

    assert result.is_valid is False
    conflict_issues = [i for i in result.issues if i.category == "plausibility"]
    assert len(conflict_issues) == 1
    assert conflict_issues[0].severity == "critical"


def test_validate_clinical_laterality_warning():
    """Test laterality warning for musculoskeletal codes."""
    result = validate_clinical(
        "cv-4",
        ["M17.11"],  # Knee OA — requires laterality context
        "Patient has knee osteoarthritis, moderate severity",
    )

    laterality_issues = [i for i in result.issues if i.category == "laterality"]
    assert len(laterality_issues) == 1


def test_validate_clinical_laterality_present():
    """Test no laterality warning when documentation specifies side."""
    result = validate_clinical(
        "cv-5",
        ["M17.11"],
        "Patient has right knee osteoarthritis",
    )

    laterality_issues = [i for i in result.issues if i.category == "laterality"]
    assert len(laterality_issues) == 0


def test_clinical_validity_report():
    """Test aggregated clinical validity report."""
    report = ClinicalValidityReport()
    report.add(validate_clinical("c1", ["I10"], "hypertension"))
    report.add(validate_clinical("c2", ["E11.42"], "type 2 diabetes bilateral neuropathy"))

    assert report.total_cases == 2
    assert report.valid_count == 2

    d = report.to_dict()
    assert d["validity_rate"] > 0


# ============================================================================
# Compliance Rate Tests
# ============================================================================


def test_evaluate_compliance_all_detected():
    """Test all expected issues detected."""
    result = evaluate_compliance(
        "cr-1",
        expected_issues=["missing laterality", "upcoding risk"],
        detected_issues=["laterality not specified for code", "potential upcoding identified"],
    )

    assert result.all_detected is True
    assert result.detection_rate == 1.0


def test_evaluate_compliance_partial_detection():
    """Test partial issue detection."""
    result = evaluate_compliance(
        "cr-2",
        expected_issues=["missing laterality", "upcoding risk", "bundling error"],
        detected_issues=["laterality not specified"],
    )

    assert result.detection_rate < 1.0
    assert len(result.false_negatives) == 2


def test_evaluate_compliance_no_expected():
    """Test when no issues are expected."""
    result = evaluate_compliance("cr-3", expected_issues=[], detected_issues=[])

    assert result.detection_rate == 1.0
    assert result.all_detected is True


def test_evaluate_compliance_false_positives():
    """Test false positive detection."""
    result = evaluate_compliance(
        "cr-4",
        expected_issues=[],
        detected_issues=["phantom issue found"],
    )

    assert len(result.false_positives) == 1
    assert result.precision == 0.0


def test_compliance_rate_report():
    """Test aggregated compliance report."""
    report = ComplianceRateReport(target_detection_rate=0.9)
    report.add(evaluate_compliance("c1", ["issue A"], ["issue A detected"]))
    report.add(evaluate_compliance("c2", [], []))

    assert report.total_cases == 2
    assert report.mean_detection_rate == 1.0
    assert report.meets_target is True

    d = report.to_dict()
    assert d["all_detected_count"] == 2


# ============================================================================
# Hallucination Audit Tests
# ============================================================================


def test_audit_no_hallucinations():
    """Test clean audit when all items traceable."""
    result = audit_hallucinations(
        "ha-1",
        source_note="Patient has hypertension and takes lisinopril daily.",
        predicted_codes=["I10"],
        output_diagnoses=["hypertension"],
        output_medications=["lisinopril"],
    )

    assert result.is_clean is True
    assert result.traceability_rate == 1.0
    assert result.items_checked == 3  # 1 code + 1 diagnosis + 1 medication


def test_audit_detects_hallucination():
    """Test hallucination detected for fabricated diagnosis."""
    result = audit_hallucinations(
        "ha-2",
        source_note="Patient has hypertension.",
        predicted_codes=["I10"],
        output_diagnoses=["hypertension", "type 2 diabetes mellitus"],
    )

    assert result.is_clean is False
    assert result.hallucination_count == 1
    assert result.findings[0].category == "diagnosis"
    assert "diabetes" in result.findings[0].content.lower()


def test_audit_detects_fabricated_medication():
    """Test hallucination detected for fabricated medication."""
    result = audit_hallucinations(
        "ha-3",
        source_note="Patient takes lisinopril for blood pressure.",
        predicted_codes=[],
        output_medications=["lisinopril", "metformin"],
    )

    assert result.hallucination_count == 1
    assert result.findings[0].category == "medication"


def test_audit_empty_output():
    """Test audit with no output items."""
    result = audit_hallucinations(
        "ha-4",
        source_note="Patient presents for routine checkup.",
        predicted_codes=[],
    )

    assert result.is_clean is True
    assert result.items_checked == 0
    assert result.traceability_rate == 1.0


def test_audit_token_overlap_matching():
    """Test token overlap matching for paraphrased content."""
    result = audit_hallucinations(
        "ha-5",
        source_note="Patient complains of severe chest pain radiating to left arm.",
        predicted_codes=[],
        output_findings=["chest pain with left arm radiation"],
    )

    # "chest", "pain", "left", "arm" should all match
    assert result.is_clean is True


def test_hallucination_audit_report():
    """Test aggregated hallucination report."""
    report = HallucinationAuditReport()
    report.add(audit_hallucinations("h1", "hypertension", [], output_diagnoses=["hypertension"]))
    report.add(audit_hallucinations("h2", "headache", [], output_diagnoses=["migraine"]))

    assert report.total_cases == 2
    assert report.clean_count == 1

    d = report.to_dict()
    assert d["total_hallucinations"] == 1


def test_hallucination_audit_report_meets_target():
    """Test hallucination target (zero tolerance)."""
    report = HallucinationAuditReport(target_traceability=1.0)
    report.add(audit_hallucinations("h1", "hypertension", [], output_diagnoses=["hypertension"]))

    assert report.meets_target is True
