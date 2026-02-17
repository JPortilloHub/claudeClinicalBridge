# Claude Clinical Bridge

> AI-powered healthcare clinical documentation and coding assistant using Claude Agent SDK and Model Context Protocol (MCP)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Tests: 225 passed](https://img.shields.io/badge/tests-225%20passed-brightgreen.svg)]()

## Overview

**Claude Clinical Bridge** is a multi-agent AI pipeline that processes unstructured physician notes end-to-end: structuring documentation, suggesting medical codes, validating compliance, handling prior authorization, and performing quality assurance. It connects to real EHR systems (Epic and Oracle Health/Cerner) via FHIR R4 APIs and uses semantic vector search over ICD-10 and CPT code databases.

### What It Does

1. **Structures clinical notes** - Converts free-text physician notes into standardized SOAP format
2. **Suggests medical codes** - Recommends ICD-10-CM diagnosis codes and CPT procedure codes with rationale
3. **Validates compliance** - Checks coding against documentation standards, payer rules, and CMS guidelines
4. **Handles prior authorization** - Assembles prior auth requests with medical necessity justification
5. **Quality assurance** - Final review scoring consistency, accuracy, hallucination risk, and submission readiness

## Architecture

```
                         Physician Note (text)
                                │
                                ▼
                    ┌───────────────────────┐
                    │   main.py (CLI)       │
                    └───────────┬───────────┘
                                │
                                ▼
            ┌───────────────────────────────────────┐
            │  ClinicalPipelineCoordinator           │
            │  (5-phase sequential pipeline)         │
            └───────────────────────────────────────┘
                    │           │           │
        ┌───────────┼───────────┼───────────┼──────────┐
        ▼           ▼           ▼           ▼          ▼
 ┌────────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐ ┌────┐
 │ Clinical   │ │ Medical  │ │Compliance│ │ Prior  │ │ QA │
 │ Doc Agent  │ │ Coding   │ │  Agent   │ │  Auth  │ │Agent│
 │            │ │  Agent   │ │          │ │ Agent  │ │    │
 └─────┬──────┘ └────┬─────┘ └────┬─────┘ └───┬────┘ └──┬─┘
       │              │            │           │        │
       └──────────────┴────────────┴───────────┴────────┘
                               │
                   ┌───────────┴───────────┐
                   ▼                       ▼
           ┌──────────────┐        ┌──────────────┐
           │  MCP Servers │        │    Skills    │
           ├──────────────┤        ├──────────────┤
           │ Epic FHIR    │        │ Med Terminol │
           │ Oracle Health│        │ Coding Accur │
           │ Med Knowledge│        │ Clin Reasong │
           │ Payer Policy │        │ Reg Complnce │
           └──────────────┘        └──────────────┘
```

### Pipeline Flow

| Phase | Agent | Input | Output |
|-------|-------|-------|--------|
| 1 | Clinical Documentation | Raw physician note | Structured SOAP documentation |
| 2 | Medical Coding | Structured documentation | ICD-10 + CPT code suggestions |
| 3 | Compliance | Documentation + Codes | Validation results, audit readiness score |
| 4 | Prior Authorization* | Procedure + Payer + Docs | Auth assessment, approval likelihood |
| 5 | Quality Assurance | All prior outputs | Quality score (0-100), submission readiness |

*Phase 4 runs only when `payer` and `procedure` are provided and `--skip-prior-auth` is not set.

---

## Sub-Agents (5)

Each agent extends `BaseAgent`, receives markdown-based skills injected into its system prompt, and calls the Anthropic API via tool use.

### 1. Clinical Documentation Agent
- **Purpose**: Structures unstructured physician notes into SOAP format
- **Skills**: `medical_terminology`, `clinical_reasoning`
- **Output**: Chief complaint, HPI, ROS, PMH, objective findings, assessment with diagnoses, treatment plan, documentation gaps

### 2. Medical Coding Agent
- **Purpose**: Suggests ICD-10-CM and CPT codes based on structured documentation
- **Skills**: `coding_accuracy`, `medical_terminology`
- **Output**: ICD-10 codes with specificity checks, CPT codes with modifiers, E/M level calculations, coding rationale

### 3. Compliance Agent
- **Purpose**: Validates coding against documentation standards, payer requirements, and regulatory guidelines
- **Skills**: `regulatory_compliance`, `coding_accuracy`
- **Output**: Code validations, E/M validation, compliance issues (upcoding/unbundling/sequencing), audit readiness score

### 4. Prior Authorization Agent
- **Purpose**: Assembles prior authorization requests with clinical justification
- **Skills**: `regulatory_compliance`, `clinical_reasoning`
- **Output**: Criteria alignment, documentation checklist, medical necessity summary, approval likelihood

### 5. Quality Assurance Agent
- **Purpose**: Final gatekeeper reviewing all outputs for consistency, accuracy, and completeness
- **Skills**: All 4 skills
- **Output**: Quality score (0-100), dimension breakdowns, hallucination detection, ready-for-submission flag

---

## Skills (4)

Skills are markdown files loaded at runtime and injected into agent system prompts. They encode domain expertise as structured prompt instructions.

| Skill | File | Used By | Purpose |
|-------|------|---------|---------|
| Medical Terminology | `medical_terminology_skill.md` | Doc, Coding, QA | SNOMED CT / ICD-10 aligned term standardization |
| Coding Accuracy | `coding_accuracy_skill.md` | Coding, Compliance, QA | ICD-10-CM/CPT rules, sequencing, bundling, E/M levels |
| Clinical Reasoning | `clinical_reasoning_skill.md` | Doc, Prior Auth, QA | Differential diagnosis, VINDICATE mnemonic, evidence-based logic |
| Regulatory Compliance | `regulatory_compliance_skill.md` | Compliance, Prior Auth, QA | HIPAA (18 identifiers), CMS guidelines, CDI rules, audit readiness |

---

## MCP Servers (4)

Four [Model Context Protocol](https://modelcontextprotocol.io/) servers built with FastMCP provide tools that agents can call during pipeline execution.

### 1. Epic FHIR Server (`epic-fhir`)
Connects to Epic's SMART on FHIR sandbox for patient data retrieval.

| Tool | Description |
|------|-------------|
| `search_patients` | Search by name, DOB, or MRN |
| `get_patient` | Retrieve demographics by FHIR ID |
| `get_patient_encounters` | Visits and appointments |
| `get_patient_conditions` | Diagnoses with clinical status |
| `get_patient_observations` | Labs and vitals |
| `get_patient_medications` | Active/stopped medications |
| `get_patient_everything` | Comprehensive patient bundle |

### 2. Oracle Health FHIR Server (`oracle-health-fhir`)
Connects to Oracle Health (Cerner) FHIR R4 sandbox.

| Tool | Description |
|------|-------------|
| `search_patients` | Search by family/given name, birthdate, identifier |
| `get_patient` | Patient by ID |
| `get_patient_encounters` | Encounters with status filtering |
| `get_patient_conditions` | Conditions with category filtering |
| `get_patient_observations` | Labs/vitals with date range |
| `get_patient_medications` | Medication requests |
| `get_patient_everything` | Selective resource bundle |

### 3. Medical Knowledge Server (`medical-knowledge`)
Semantic vector search over ICD-10 and CPT code databases using BioBERT embeddings and Qdrant.

| Tool | Description |
|------|-------------|
| `search_icd10` | Natural language search for diagnosis codes (e.g., "high blood sugar" -> E11.9) |
| `search_cpt` | Natural language search for procedure codes (e.g., "routine office visit" -> 99214) |
| `get_code_details` | Exact code lookup with full metadata |
| `get_code_hierarchy` | Parent/child code relationships |
| `get_collection_stats` | Vector database statistics |

### 4. Payer Policy Server (`payer-policy`)
In-memory policy database for prior authorization rules and documentation requirements.

| Tool | Description |
|------|-------------|
| `check_auth_requirements` | Check if procedure requires prior auth for a given payer |
| `get_documentation_requirements` | Required documentation elements and medical necessity criteria |
| `validate_medical_necessity` | Validate clinical data against payer-specific criteria |

---

## Quick Start

### Prerequisites

- **Python 3.10+** - [Download](https://www.python.org/downloads/)
- **Poetry** - [Install](https://python-poetry.org/docs/#installation)
- **Docker & Docker Compose** - [Install](https://docs.docker.com/get-docker/)
- **Anthropic API Key** - [Get API Key](https://console.anthropic.com/)
- **Epic FHIR Sandbox** (optional) - [Register](https://fhir.epic.com/Developer/Apps)
- **Oracle Health Developer** (optional) - [Register](https://code.cerner.com/developer/smart-on-fhir/)

### Installation

```bash
# Clone
git clone https://github.com/yourusername/claudeClinicalBridge.git
cd claudeClinicalBridge

# Install dependencies
poetry install

# Configure environment
cp .env.example .env
# Edit .env with your API keys

# Start local services (Qdrant, PostgreSQL, Redis)
docker-compose up -d
```

### Configuration

Edit `.env` with your credentials:

```bash
# Required
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Optional (for FHIR integration)
EPIC_CLIENT_ID=your_epic_client_id
EPIC_CLIENT_SECRET=your_epic_client_secret

ORACLE_CLIENT_ID=your_oracle_health_client_id
ORACLE_CLIENT_SECRET=your_oracle_health_client_secret
```

See [.env.example](.env.example) for all configuration options.

---

## Usage

### CLI (main.py)

The CLI entry point runs the full 5-phase pipeline against the Anthropic API.

```bash
# Inline note
python main.py "65yo male with chest pain, BP 160/95, history of HTN and T2DM"

# From file
python main.py --file note.txt

# With payer and procedure (enables prior authorization phase)
python main.py --file note.txt --payer "Medicare" --procedure "99214"

# Skip prior authorization
python main.py --file note.txt --payer "Medicare" --skip-prior-auth

# JSON output
python main.py --file note.txt --output json

# Full output (all phase details)
python main.py --file note.txt --output full

# With patient ID (for FHIR lookups)
python main.py --file note.txt --patient-id P123 --payer "Aetna" --procedure "70553"
```

| Argument | Required | Description |
|----------|----------|-------------|
| `note` (positional) | One of note/--file | Inline clinical note text |
| `--file`, `-f` | One of note/--file | Path to a text file containing the note |
| `--patient-id` | No | FHIR patient identifier |
| `--payer` | No | Payer name (e.g., Medicare, Aetna) |
| `--procedure` | No | Procedure description or CPT code |
| `--skip-prior-auth` | No | Skip the prior authorization phase |
| `--output`, `-o` | No | Output format: `summary` (default), `json`, `full` |

**Note**: Each pipeline run makes 4-5 Anthropic API calls (one per active phase).

### Programmatic Usage

```python
import anthropic
from src.python.orchestration.coordinator import ClinicalPipelineCoordinator

client = anthropic.Anthropic(api_key="your-key")
coordinator = ClinicalPipelineCoordinator(client=client)

state = coordinator.process_note(
    note="65yo M presents with chest pain...",
    patient_id="epic-patient-123",
    payer="Medicare",
    procedure="99214",
)

print(state.status)           # completed / failed / needs_review
print(state.to_summary())     # Full result dict
```

---

## Development

### Project Structure

```
claudeClinicalBridge/
├── main.py                     # CLI entry point
├── src/python/
│   ├── agents/                 # 5 sub-agents (Claude Agent SDK)
│   │   ├── base_agent.py
│   │   ├── clinical_documentation.py
│   │   ├── medical_coding.py
│   │   ├── compliance.py
│   │   ├── prior_authorization.py
│   │   └── quality_assurance.py
│   ├── skills/                 # 4 markdown-based skills
│   │   ├── skill_loader.py
│   │   ├── medical_terminology_skill.md
│   │   ├── coding_accuracy_skill.md
│   │   ├── clinical_reasoning_skill.md
│   │   └── regulatory_compliance_skill.md
│   ├── mcp_servers/            # 4 MCP server implementations
│   │   ├── epic_fhir/
│   │   ├── oracle_fhir/
│   │   ├── medical_knowledge/
│   │   └── payer_policy/
│   ├── orchestration/          # Pipeline coordinator & workflow
│   │   ├── coordinator.py
│   │   ├── workflow.py
│   │   └── state.py
│   ├── evaluation/             # Evaluation framework (5 metrics)
│   ├── fhir/                   # Shared FHIR base client
│   ├── security/               # HIPAA compliance utilities
│   └── utils/                  # Configuration and logging
├── tests/                      # Unit, integration, and evaluation tests
│   ├── unit/
│   ├── integration/
│   └── evaluation/
├── data/                       # Medical code datasets
├── docker-compose.yml          # Qdrant, PostgreSQL, Redis
└── pyproject.toml              # Poetry dependencies
```

### Running Tests

```bash
# Run all tests (225 passing)
poetry run pytest

# Run with coverage
poetry run pytest --cov=src --cov-report=html

# Run specific test suite
poetry run pytest tests/unit/
poetry run pytest tests/integration/
poetry run pytest tests/evaluation/
```

### Code Quality

```bash
# Lint
poetry run ruff check .

# Format
poetry run ruff format .

# Type checking
poetry run mypy src/

# Security scan
poetry run bandit -r src/python/ -ll
```

---

## Evaluation Framework

Five metrics assess pipeline quality:

| Metric | Target | Description |
|--------|--------|-------------|
| Coding Accuracy | >90% | ICD-10/CPT codes compared against expert coders |
| Clinical Validity | Pass | Medical professional review of documentation quality |
| Compliance Catch Rate | >85% | Detection rate for documentation gaps and coding issues |
| Hallucination Audit | <5% | Percentage of claims not traceable to source note |
| End-to-End Latency | <30s | Total pipeline execution time |

---

## HIPAA Compliance

- **PHI Redaction** - Automatic detection and redaction of PHI in logs (18 HIPAA identifiers)
- **Audit Logging** - All patient data access logged with timestamps
- **Encryption** - Data encrypted at rest (tokens, cached FHIR data)
- **Minimum Necessary** - Only required patient data accessed

---

## Roadmap

### Completed
- [x] Project structure, configuration, Docker Compose
- [x] 4 MCP Servers (Epic FHIR, Oracle Health, Medical Knowledge, Payer Policy)
- [x] 4 Agent Skills (markdown-based prompt engineering)
- [x] 5 Sub-Agents (Claude Agent SDK)
- [x] Orchestration Layer (5-phase pipeline)
- [x] Evaluation Framework (5 metrics)
- [x] HIPAA Compliance (PHI redaction, audit logging, encryption)
- [x] Integration Tests
- [x] CLI Entry Point (`main.py`)

### Future
- [ ] Human-in-the-Loop UI (TypeScript/React)
- [ ] Real-time dictation support
- [ ] Learning from corrections
- [ ] Multi-modal support (images, PDFs)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- **Anthropic** - Claude API and Agent SDK
- **Epic Systems** - FHIR sandbox access
- **Oracle Health** - Developer program and FHIR APIs
- **CDC/CMS** - Public ICD-10 code datasets
- **DMIS Lab** - BioBERT pre-trained model

## Disclaimer

**This is a development/research project using synthetic data and EHR sandboxes.**

**NOT FOR PRODUCTION USE WITH REAL PATIENT DATA** without:
- Proper HIPAA Business Associate Agreements (BAA) with all vendors
- Security audit and penetration testing
- CPT code licensing from AMA (if using full CPT dataset)
- Legal review and compliance certification
- Appropriate medical professional oversight

Always consult with certified professional coders and healthcare compliance experts before using AI-assisted coding in production.

---

**Built with Claude Agent SDK and Model Context Protocol**
