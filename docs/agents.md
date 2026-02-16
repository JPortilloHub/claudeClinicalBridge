# Agents

This document describes the 5 sub-agents that form the clinical documentation pipeline.

## Overview

All agents extend `BaseAgent` (`src/python/agents/base_agent.py`), which provides:
- Anthropic Messages API integration via `anthropic.Anthropic` client
- Automatic skill loading from Markdown files via `skill_loader`
- System prompt construction (agent instructions + loaded skills)
- Standardized `run()` method with error handling

## Agent Pipeline

```
Raw Clinical Note
       |
       v
[1. Clinical Documentation Agent]  --> Structured SOAP note
       |
       v
[2. Medical Coding Agent]          --> ICD-10 + CPT codes
       |
       v
[3. Compliance Agent]              --> Validation + flags
       |
       v
[4. Prior Authorization Agent]     --> Auth request (if needed)
       |
       v
[5. Quality Assurance Agent]       --> Final approval / review flags
```

---

## 1. Clinical Documentation Agent

**File**: `src/python/agents/clinical_documentation.py`
**Class**: `ClinicalDocumentationAgent`

### Purpose
Transforms unstructured physician notes into standardized clinical documentation (SOAP format or E/M components).

### Skills
- `medical_terminology` - Precise medical language and abbreviation expansion
- `clinical_reasoning` - Differential diagnosis and clinical relationships

### Key Method
```python
async def structure_note(note: str, patient_context: str = "") -> str
```

### Output Format
Structured note with sections: Chief Complaint, History of Present Illness (HPI), Review of Systems (ROS), Physical Examination, Assessment, and Plan.

---

## 2. Medical Coding Agent

**File**: `src/python/agents/medical_coding.py`
**Class**: `MedicalCodingAgent`

### Purpose
Suggests accurate ICD-10-CM diagnosis codes and CPT procedure codes based on the structured documentation.

### Skills
- `coding_accuracy` - ICD-10/CPT selection rules, specificity, sequencing
- `medical_terminology` - Precise medical language

### Key Method
```python
async def suggest_codes(structured_note: str, patient_context: str = "") -> str
```

### Output
- Primary diagnosis code with ICD-10-CM
- Secondary diagnosis codes
- CPT procedure codes
- Code justification linked to documentation

---

## 3. Compliance Agent

**File**: `src/python/agents/compliance.py`
**Class**: `ComplianceAgent`

### Purpose
Validates that suggested codes are supported by documentation and meet payer requirements. Identifies compliance risks.

### Skills
- `regulatory_compliance` - HIPAA, audit requirements, upcoding/downcoding detection
- `coding_accuracy` - Code validation rules

### Key Method
```python
async def validate(structured_note: str, codes: str, payer: str = "") -> str
```

### Checks Performed
- Code-to-documentation support
- Documentation completeness per payer requirements
- Upcoding/downcoding risk
- Missing laterality or specificity
- Bundling and modifier compliance

---

## 4. Prior Authorization Agent

**File**: `src/python/agents/prior_authorization.py`
**Class**: `PriorAuthorizationAgent`

### Purpose
Determines if procedures require prior authorization and assembles authorization requests with clinical justification.

### Skills
- `regulatory_compliance` - Authorization requirements
- `clinical_reasoning` - Medical necessity justification

### Key Method
```python
async def assess_authorization(codes: str, clinical_data: str, payer: str = "") -> str
```

### Output
- Whether prior auth is required
- Clinical justification narrative
- Supporting documentation references
- Medical necessity criteria mapping

### Pipeline Behavior
Phase 4 is **non-fatal** — if prior auth assessment fails, the pipeline continues and marks the workflow for review rather than failing entirely.

---

## 5. Quality Assurance Agent

**File**: `src/python/agents/quality_assurance.py`
**Class**: `QualityAssuranceAgent`

### Purpose
Final gatekeeper that reviews all agent outputs for consistency, accuracy, and completeness.

### Skills
All four skills:
- `medical_terminology`
- `coding_accuracy`
- `clinical_reasoning`
- `regulatory_compliance`

### Key Method
```python
async def review(workflow_summary: str) -> str
```

### Checks Performed
- Internal consistency across all phases
- Code accuracy against documentation
- Clinical validity of diagnoses
- Hallucination detection (claims not in source note)
- Completeness of documentation

### Pipeline Behavior
Phase 5 failure results in `NEEDS_REVIEW` status (not full failure), flagging the case for human review.

---

## BaseAgent Configuration

| Property | Type | Description |
|----------|------|-------------|
| `agent_name` | `str` | Unique identifier |
| `agent_description` | `str` | Human-readable description |
| `required_skills` | `tuple[str, ...]` | Skills loaded into system prompt |

### Usage Example

```python
from src.python.agents.medical_coding import MedicalCodingAgent

agent = MedicalCodingAgent()
result = await agent.suggest_codes(
    structured_note="Chief Complaint: Chest pain...",
    patient_context="65yo male, history of HTN"
)
```
