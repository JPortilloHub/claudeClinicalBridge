# Evaluation Framework

This document describes the evaluation metrics, targets, and tools for measuring system quality.

## Overview

The evaluation framework measures 5 key metrics across the clinical documentation pipeline:

| Metric | Module | Target | Description |
|--------|--------|--------|-------------|
| Coding Accuracy | `coding_accuracy.py` | F1 >= 0.90 | ICD-10/CPT code correctness |
| Clinical Validity | `clinical_validity.py` | Validity rate >= 0.95 | Medical correctness of outputs |
| Compliance Catch Rate | `compliance_rate.py` | Detection rate >= 0.85 | Ability to flag documentation gaps |
| Hallucination Audit | `hallucination_audit.py` | Traceability >= 0.95 | Detect fabricated clinical claims |
| End-to-End Latency | `latency_tracker.py` | p90 < 30s | Workflow timing |

All modules are in `src/python/evaluation/`.

## Metrics Detail

### Coding Accuracy

Compares predicted ICD-10/CPT codes against a ground truth dataset.

**Calculations** (per case):
- **Precision**: Correct predicted / Total predicted
- **Recall**: Correct predicted / Total expected
- **F1 Score**: Harmonic mean of precision and recall
- **Exact Match**: Whether predicted set equals expected set exactly

**Aggregated report** (`CodingAccuracyReport`):
- Mean precision, recall, F1 across all cases
- Exact match rate
- Target check: mean F1 >= target (default 0.90)

**Usage**:
```python
from src.python.evaluation.coding_accuracy import evaluate_codes, CodingAccuracyReport

result = evaluate_codes("case-1", expected=["I10", "E11.42"], predicted=["I10", "E11.42"])
# result.f1_score == 1.0

report = CodingAccuracyReport(target_accuracy=0.90)
report.add(result)
print(report.meets_target)  # True
```

Code comparison is **case-insensitive** (e.g., `i10` matches `I10`).

### Clinical Validity

Validates that codes are clinically appropriate for the documented conditions.

**Checks**:
1. **Specificity**: Flags 3-character ICD-10 codes that should have more digits
2. **Laterality**: Warns when musculoskeletal/injury codes lack left/right specification in documentation
3. **Conflicting Codes**: Detects known conflict pairs (e.g., Type 1 + Type 2 diabetes: E10 + E11)

**Known Conflict Pairs**:
- `E10` / `E11` (Type 1 vs Type 2 diabetes)
- `I10` / `I15` (Primary vs Secondary hypertension)
- `J44` / `J45` (COPD vs Asthma)

**Laterality-Required Prefixes**: M1, M2, S, T, H0-H5, G5

**Scoring**: Overall score (0.0-1.0) based on weighted issues:
- Critical issues (conflicts): -0.4 per issue
- Warning issues (specificity, laterality): -0.1 per issue

### Compliance Catch Rate

Measures the system's ability to detect expected compliance issues.

**Matching**: Keyword-based fuzzy matching that:
1. Tokenizes expected and detected issues into words
2. Removes stop words (the, a, is, for, etc.)
3. Checks if >= 50% of expected keywords appear in any detected issue

**Metrics**:
- **Detection rate**: Fraction of expected issues that were detected
- **False negatives**: Expected issues that were missed
- **False positives**: Detected issues not matching any expected issue
- **Precision**: True positives / (True positives + False positives)

### Hallucination Audit

Detects fabricated clinical information by checking traceability to the source note.

**Two-pass matching**:
1. **Substring match**: Check if the output item (or significant words) appear directly in the source note
2. **Token overlap**: Tokenize both, check if >= 50% of output tokens appear in the source (handles paraphrasing)

**Items checked**:
- Predicted codes (matched against code patterns in source)
- Output diagnoses
- Output medications
- Output findings

**Metrics**:
- **Traceability rate**: Fraction of items traceable to source
- **Hallucination count**: Number of untraceable items
- **is_clean**: Whether zero hallucinations were found

### Latency Tracking

Measures execution time for workflow phases and overall pipeline.

**Usage**:
```python
from src.python.evaluation.latency_tracker import track_latency, LatencyReport

report = LatencyReport(target_seconds=30.0)

with track_latency("coding_phase", report) as record:
    # ... do work ...
    pass

print(report.p90_seconds)  # 90th percentile latency
print(report.meets_target)  # True if p90 < target
```

**Statistics**: mean, median, min, max, p90, within_target_rate.

## Golden Dataset

**Location**: `tests/evaluation/test_cases/golden_dataset.json`

Contains synthetic clinical scenarios with ground truth:

```json
{
  "case_id": "GOLD-001",
  "clinical_note": "...",
  "expected_icd10": ["I10", "E11.42"],
  "expected_cpt": ["99214"],
  "expected_diagnoses": ["essential hypertension", ...],
  "expected_medications": ["lisinopril", ...],
  "expected_compliance_issues": []
}
```

## Running Evaluations

### Command Line

```bash
# Full evaluation with default dataset
python scripts/run_evaluation.py

# Custom dataset
python scripts/run_evaluation.py --dataset path/to/dataset.json

# Save report to file
python scripts/run_evaluation.py --output report.json
```

### CI/CD

The `evaluation.yml` GitHub Action runs weekly and on manual trigger. Reports are uploaded as workflow artifacts.

### Interpreting Results

The evaluation runner outputs a summary with per-metric pass/fail:

```
=== Evaluation Report ===
Coding Accuracy:    PASS (F1: 0.93, target: 0.90)
Clinical Validity:  PASS (validity: 0.96, target: 0.95)
Compliance Rate:    PASS (detection: 0.88, target: 0.85)
Hallucination:      PASS (traceability: 0.97, target: 0.95)
Latency:            PASS (p90: 2.1s, target: 30.0s)

Overall: PASS
```

A metric fails if it does not meet its target. Overall result is PASS only if all metrics pass.
