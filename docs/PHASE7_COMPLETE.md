# Phase 7: Orchestration Layer - Complete

## Overview

Phase 7 implements the orchestration layer that coordinates multi-agent execution for the clinical documentation and coding pipeline. It manages workflow state, retry logic, and sequential phase execution.

## Architecture

```
src/python/orchestration/
├── __init__.py          # Package exports
├── state.py             # WorkflowState, PhaseResult, status enums
├── workflow.py          # Retry logic and phase execution utilities
└── coordinator.py       # ClinicalPipelineCoordinator

tests/unit/test_orchestration/
└── test_orchestration.py  # 26 unit tests (all passing)
```

## Components

### WorkflowState (`state.py`)

Maintains state across the clinical pipeline execution:

- **WorkflowStatus** enum: `PENDING`, `IN_PROGRESS`, `COMPLETED`, `FAILED`, `NEEDS_REVIEW`
- **PhaseStatus** enum: `PENDING`, `RUNNING`, `COMPLETED`, `FAILED`, `SKIPPED`
- **PhaseResult** dataclass: Tracks individual phase name, agent, status, content, error, usage, and timing
- **WorkflowState** dataclass: Holds input data, 5 PhaseResults, and workflow metadata
- Properties: `total_duration_seconds`, `total_tokens`, `completed_phases`, `failed_phases`, `to_summary()`

### Workflow Utilities (`workflow.py`)

- **`run_with_retry(fn, *args, max_retries, base_delay, **kwargs)`**: Exponential backoff retry for agent calls. Retries on agent-level errors (result contains `error` key). Defaults to `settings.agent_max_retries` attempts.
- **`execute_phase(phase, fn, *args, use_retry, **kwargs)`**: Wraps agent execution with PhaseResult state tracking — marks running, completed, or failed with timing.

### ClinicalPipelineCoordinator (`coordinator.py`)

Orchestrates the full 5-phase pipeline:

1. **Clinical Documentation** — structures raw note into SOAP format
2. **Medical Coding** — suggests ICD-10/CPT codes from structured doc
3. **Compliance** — validates codes against documentation
4. **Prior Authorization** — assembles auth request (conditional: requires payer + procedure)
5. **Quality Assurance** — final gatekeeper review

**Error handling**:
- Phases 1-3 are **fatal** — failure stops the pipeline
- Phase 4 (prior auth) is **non-fatal** — failure continues to QA
- Phase 5 (QA) failure results in `NEEDS_REVIEW` status
- Unexpected exceptions are caught and logged

## Pipeline Flow

```
Raw Note → [Clinical Documentation] → Structured SOAP
                ↓ (fatal on error)
         [Medical Coding] → ICD-10/CPT Codes
                ↓ (fatal on error)
         [Compliance] → Validation Results
                ↓ (fatal on error)
         [Prior Auth] → Auth Assessment (skipped if no payer/procedure)
                ↓ (non-fatal)
         [Quality Assurance] → Final Review
```

## Test Results

```
26 passed in 14.43s
```

- 5 PhaseResult tests (init, running, completed, failed, skipped)
- 6 WorkflowState tests (init, lifecycle, tokens, filtering, summary)
- 4 retry tests (success, retry-then-success, exhaustion, exponential backoff)
- 3 execute_phase tests (success, failure, with retry)
- 8 coordinator tests (init, full pipeline, skip prior auth, auto-skip, failures, context, summary)

## Usage

```python
from src.python.orchestration import ClinicalPipelineCoordinator

# Initialize with shared Anthropic client
coordinator = ClinicalPipelineCoordinator(client=client)

# Process a clinical note
state = coordinator.process_note(
    note="65yo M with chest pain, elevated BP 160/95...",
    patient_id="P001",
    payer="Medicare",
    procedure="99214",
)

# Check results
print(state.status)                    # WorkflowStatus.COMPLETED
print(state.documentation.content)     # Structured SOAP JSON
print(state.coding.content)            # ICD-10/CPT suggestions
print(state.to_summary())             # Full workflow summary
```
