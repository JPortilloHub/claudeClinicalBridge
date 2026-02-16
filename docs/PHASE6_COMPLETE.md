# Phase 6: Sub-Agents - Complete

## Overview

Phase 6 implements 5 Claude Agent SDK sub-agents and a shared base agent class. Each agent has a specific role in the clinical documentation and coding pipeline, loads relevant skills from Phase 5, and communicates via the Anthropic Messages API.

## Architecture

```
src/python/agents/
├── __init__.py                   # Package exports
├── base_agent.py                 # BaseAgent with shared patterns
├── clinical_documentation.py     # Structures physician notes → SOAP
├── medical_coding.py             # Suggests ICD-10 and CPT codes
├── compliance.py                 # Validates coding compliance
├── prior_authorization.py        # Assembles prior auth requests
└── quality_assurance.py          # Final gatekeeper review

tests/unit/test_agents/
└── test_agents.py                # 20 unit tests (all passing)
```

## BaseAgent

Shared functionality for all agents:

- Anthropic client initialization (from settings or injected)
- Skill loading into system prompts via `load_skills()`
- Structured message building with optional context
- Timeout and API error handling
- Structured result format: `{content, agent, model, usage, stop_reason}`

## Sub-Agents

### 1. Clinical Documentation Agent
- **Role**: Structures unstructured physician notes into SOAP format
- **Skills**: medical_terminology, clinical_reasoning
- **Method**: `structure_note(raw_note, context)`
- **Output**: SOAP-structured JSON with documentation gaps and coding hints

### 2. Medical Coding Agent
- **Role**: Suggests ICD-10-CM and CPT codes from documentation
- **Skills**: coding_accuracy, medical_terminology
- **Method**: `suggest_codes(documentation, context)`
- **Output**: Diagnosis codes, procedure codes, E/M calculation, queries needed

### 3. Compliance Agent
- **Role**: Validates coding against documentation and regulations
- **Skills**: regulatory_compliance, coding_accuracy
- **Method**: `validate(documentation, suggested_codes, context)`
- **Output**: Compliance status, code validations, risk level, audit readiness score

### 4. Prior Authorization Agent
- **Role**: Assembles prior auth requests with criteria assessment
- **Skills**: regulatory_compliance, clinical_reasoning
- **Method**: `assess_authorization(procedure, payer, clinical_data, context)`
- **Output**: Criteria met/unmet, documentation checklist, approval likelihood

### 5. Quality Assurance Agent
- **Role**: Final gatekeeper reviewing all pipeline outputs
- **Skills**: All 4 skills
- **Method**: `review(source_note, documentation, coding, compliance, context)`
- **Output**: Quality scores (5 dimensions), hallucination check, traceability

## Agent-to-Skill Mapping

| Agent | medical_terminology | coding_accuracy | clinical_reasoning | regulatory_compliance |
|-------|:--:|:--:|:--:|:--:|
| Clinical Documentation | X | | X | |
| Medical Coding | X | X | | |
| Compliance | | X | | X |
| Prior Authorization | | | X | X |
| Quality Assurance | X | X | X | X |

## Pipeline Flow

```
Raw Note → [Clinical Documentation] → Structured SOAP
                                           ↓
                                    [Medical Coding] → ICD-10/CPT Codes
                                           ↓
                                    [Compliance] → Validation Results
                                           ↓
                                    [Prior Auth] → Auth Assessment (if needed)
                                           ↓
                                    [Quality Assurance] → Final Review
```

## Test Results

```
20 passed in 0.42s
```

- 7 BaseAgent tests (init, run, context, timeout, API error, message building)
- 2 tests per sub-agent (init + primary method)
- 3 cross-agent integration tests (inheritance, unique names, skill loading)
- All tests use mocked Anthropic client — no real API calls

## Usage

```python
from src.python.agents import (
    ClinicalDocumentationAgent,
    MedicalCodingAgent,
    ComplianceAgent,
    PriorAuthorizationAgent,
    QualityAssuranceAgent,
)

# Initialize with default settings (reads ANTHROPIC_API_KEY from .env)
doc_agent = ClinicalDocumentationAgent()
coding_agent = MedicalCodingAgent()

# Or inject a client
import anthropic
client = anthropic.Anthropic(api_key="sk-...")
doc_agent = ClinicalDocumentationAgent(client=client)

# Run the pipeline
doc_result = doc_agent.structure_note("Patient presents with chest pain...")
coding_result = coding_agent.suggest_codes(doc_result["content"])
```
