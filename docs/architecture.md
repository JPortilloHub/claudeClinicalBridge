# Architecture

## System Overview

Claude Clinical Bridge uses a multi-agent architecture built on the Claude Agent SDK and Model Context Protocol (MCP). The system processes unstructured clinical notes through a 5-phase pipeline, producing structured documentation, accurate medical codes, compliance validation, and prior authorization support.

## High-Level Architecture

```
                    +-----------------------+
                    |   Unstructured Note   |
                    +-----------+-----------+
                                |
                                v
                +-------------------------------+
                |   ClinicalPipelineCoordinator |
                |   (src/python/orchestration/) |
                +-------------------------------+
                    |   |   |   |   |
        +-----------+   |   |   |   +----------+
        v               v   |   v              v
  +-----------+  +--------+ | +-------+  +----------+
  | Clinical  |  |Medical | | |Compli-|  | Quality  |
  | Doc Agent |  |Coding  | | |ance   |  | Assurance|
  |           |  |Agent   | | |Agent  |  | Agent    |
  +-----------+  +--------+ | +-------+  +----------+
                             v
                       +----------+
                       | Prior    |
                       | Auth     |
                       | Agent    |
                       +----------+
        All agents use:
        +-------------------+    +----------------+
        |   MCP Servers     |    |    Skills      |
        | - Epic FHIR       |    | - Medical Term |
        | - Oracle Health   |    | - Coding Acc.  |
        | - Med Knowledge   |    | - Clinical Reas|
        | - Payer Policy    |    | - Regulatory   |
        +-------------------+    +----------------+
                |
        +-------------------+
        |  Security Layer   |
        | - PHI Redaction   |
        | - Audit Logging   |
        | - Encryption      |
        +-------------------+
```

## Component Details

### Orchestration Layer

**Location**: `src/python/orchestration/`

The `ClinicalPipelineCoordinator` manages the 5-phase sequential pipeline:

| Phase | Agent | Fatal on Failure | Description |
|-------|-------|-----------------|-------------|
| 1 | Clinical Documentation | Yes | Structures raw note into SOAP format |
| 2 | Medical Coding | Yes | Suggests ICD-10 and CPT codes |
| 3 | Compliance | Yes | Validates codes against payer requirements |
| 4 | Prior Authorization | No | Assembles auth request if needed |
| 5 | Quality Assurance | No (NEEDS_REVIEW) | Final consistency check |

**State management** is handled by `WorkflowState` and `PhaseResult` dataclasses that track status, timing, token usage, and content for each phase.

**Retry logic** uses exponential backoff (`base_delay * 2^attempt`) with configurable max retries (default: 3).

### Sub-Agents

**Location**: `src/python/agents/`

All agents extend `BaseAgent`, which provides:
- Anthropic Messages API integration
- Automatic skill loading from Markdown files
- System prompt construction (instructions + skills)
- Error handling and response extraction

| Agent | Skills Used | Primary MCP Tools |
|-------|------------|-------------------|
| Clinical Documentation | medical_terminology, clinical_reasoning | epic_fhir, oracle_health |
| Medical Coding | coding_accuracy, medical_terminology | medical_knowledge, payer_policy |
| Compliance | regulatory_compliance, coding_accuracy | payer_policy |
| Prior Authorization | regulatory_compliance, clinical_reasoning | payer_policy, epic_fhir |
| Quality Assurance | all 4 skills | all tools |

### MCP Servers

**Location**: `src/python/mcp_servers/`

Built with `FastMCP` from the MCP SDK. Each server exposes tools that agents call to access external data.

| Server | Transport | Data Source |
|--------|-----------|-------------|
| Epic FHIR | stdio | Epic FHIR R4 sandbox |
| Oracle Health | stdio | Oracle Health Ignite FHIR R4 |
| Medical Knowledge | stdio | Qdrant vector DB (BioBERT embeddings) |
| Payer Policy | stdio | SQLite (policy rules) |

### Skills

**Location**: `src/python/skills/`

Skills are Markdown files loaded at agent initialization. They provide domain-specific instructions, guidelines, and examples that are injected into the agent's system prompt.

The `skill_loader.py` module handles loading, caching, and listing available skills.

### Security Layer

**Location**: `src/python/security/`

Three components enforce HIPAA compliance:

1. **PHI Redactor** - Regex-based detection and redaction of 18 HIPAA Safe Harbor identifiers
2. **Audit Logger** - Append-only JSON log with SHA-256 hashed patient IDs
3. **Encryption Manager** - Fernet (AES-128-CBC + HMAC-SHA256) for data at rest

### Evaluation Framework

**Location**: `src/python/evaluation/`

Five metrics measure system quality:

| Metric | Target | Module |
|--------|--------|--------|
| Coding Accuracy (F1) | >= 90% | `coding_accuracy.py` |
| Clinical Validity | >= 95% | `clinical_validity.py` |
| Compliance Catch Rate | >= 85% | `compliance_rate.py` |
| Hallucination Rate | < 5% | `hallucination_audit.py` |
| End-to-End Latency (p90) | < 30s | `latency_tracker.py` |

## Data Flow

1. **Input**: Unstructured clinical note + patient ID + payer
2. **Phase 1**: Note structured into SOAP format (Chief Complaint, HPI, ROS, Exam, Assessment, Plan)
3. **Phase 2**: ICD-10/CPT codes suggested via semantic search + clinical reasoning
4. **Phase 3**: Codes validated against payer documentation requirements
5. **Phase 4**: Prior authorization assembled if procedure requires it
6. **Phase 5**: Final QA review for consistency and hallucination detection
7. **Output**: Structured documentation, codes, compliance status, QA approval

## Technology Stack

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| AI/Agents | Claude Agent SDK, Anthropic API | Best-in-class reasoning |
| MCP Servers | FastMCP (Python) | Standard tool protocol |
| FHIR | fhirclient, httpx | Industry-standard EHR API |
| Vector Search | Qdrant + BioBERT | Medical-domain embeddings |
| Policy Storage | SQLite | Simple local dev, production-ready upgrade path |
| Configuration | Pydantic Settings | Type-safe, env-based config |
| Logging | structlog | Structured JSON logging |
| Encryption | cryptography (Fernet) | Industry-standard symmetric encryption |
| Testing | pytest | Standard Python testing |
| CI/CD | GitHub Actions | Integrated with repository |

## Design Decisions

1. **EHR-Agnostic Design**: Epic and Oracle Health MCP servers expose identical tool interfaces. Agents don't know which EHR they query.

2. **Sequential Pipeline**: Phases run sequentially because each depends on the previous output. Prior Auth (Phase 4) is non-fatal to allow workflow completion even if auth assessment fails.

3. **Skills as Markdown**: Skills are plain Markdown files, making them easy to edit, version, and review without code changes.

4. **Immutable Agent Config**: Agent `required_skills` use tuples (not lists) to prevent accidental mutation at the class level.

5. **HIPAA from Day One**: Security is not bolted on — PHI redaction, audit logging, and encryption are core infrastructure used across all components.
