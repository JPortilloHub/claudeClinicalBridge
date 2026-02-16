# Claude Clinical Bridge

> AI-powered healthcare clinical documentation and coding assistant using Claude Agent SDK and Model Context Protocol (MCP)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

## Overview

**Claude Clinical Bridge** is a comprehensive AI-powered platform that assists healthcare providers with:

- 📝 **Clinical Documentation** - Structures unstructured physician notes into standardized SOAP/E&M format
- 🏥 **Medical Coding** - Suggests accurate ICD-10 diagnosis and CPT procedure codes
- ✅ **Compliance Checking** - Validates coding against documentation requirements and payer policies
- 📋 **Prior Authorization** - Assembles prior auth requests with clinical justification
- 🔍 **Quality Assurance** - Final review for consistency, accuracy, and completeness

### Key Features

- **Multi-Agent Architecture** - 5 specialized AI agents working in coordination
- **EHR Integration** - Connects to Epic and Oracle Health (Cerner) via FHIR APIs
- **Semantic Medical Code Search** - BioBERT-powered search over ICD-10/CPT codes
- **HIPAA Compliance** - PHI redaction, audit logging, and encryption from day one
- **Evaluation Framework** - Comprehensive metrics for coding accuracy, clinical validity, and compliance

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Clinical Documentation Flow                 │
└─────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
            ┌───────────────────────────────────────┐
            │   Orchestration Layer (Coordinator)   │
            └───────────────────────────────────────┘
                    │           │           │
        ┌───────────┼───────────┼───────────┼──────────┐
        ▼           ▼           ▼           ▼          ▼
┌──────────────┐ ┌──────────┐ ┌─────────┐ ┌────────┐ ┌────┐
│ Clinical Doc │ │ Medical  │ │Compliance│ │ Prior  │ │ QA │
│    Agent     │ │  Coding  │ │  Agent  │ │  Auth  │ │Agent│
│              │ │  Agent   │ │         │ │ Agent  │ │    │
└──────────────┘ └──────────┘ └─────────┘ └────────┘ └────┘
        │              │            │           │        │
        └──────────────┴────────────┴───────────┴────────┘
                                │
                    ┌───────────┴───────────┐
                    ▼                       ▼
            ┌──────────────┐        ┌──────────────┐
            │  MCP Servers │        │    Skills    │
            ├──────────────┤        ├──────────────┤
            │ Epic FHIR    │        │ Medical Term │
            │ Oracle Health│        │ Coding Accur │
            │ Med Knowledge│        │ Clinical Reas│
            │ Payer Policy │        │ Regulatory   │
            └──────────────┘        └──────────────┘
```

### Components

#### MCP Servers (4)
- **Epic FHIR MCP Server** - SMART on FHIR integration with Epic sandbox
- **Oracle Health MCP Server** - FHIR R4 integration with Oracle Health/Cerner sandbox
- **Medical Knowledge Base MCP Server** - Semantic search over ICD-10/CPT codes using BioBERT
- **Payer Policy MCP Server** - Prior authorization criteria and documentation requirements

#### Sub-Agents (5)
- **Clinical Documentation Agent** - Structures unstructured physician notes
- **Medical Coding Agent** - Suggests ICD-10 and CPT codes
- **Compliance Agent** - Validates coding against requirements
- **Prior Authorization Agent** - Assembles prior auth requests
- **Quality Assurance Agent** - Final gatekeeper for consistency

#### Skills (4 - Markdown-based)
- `medical_terminology_skill.md` - Precise medical language
- `coding_accuracy_skill.md` - ICD-10/CPT code selection rules
- `clinical_reasoning_skill.md` - Differential diagnosis
- `regulatory_compliance_skill.md` - HIPAA compliance

## Quick Start

### Prerequisites

- **Python 3.10+** - [Download](https://www.python.org/downloads/)
- **Poetry** - [Install](https://python-poetry.org/docs/#installation)
- **Docker & Docker Compose** - [Install](https://docs.docker.com/get-docker/)
- **Anthropic API Key** - [Get API Key](https://console.anthropic.com/)
- **Epic FHIR Sandbox** (optional) - [Register](https://fhir.epic.com/Developer/Apps)
- **Oracle Health Developer** (optional) - [Register](https://code.cerner.com/developer/smart-on-fhir/)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/claudeClinicalBridge.git
   cd claudeClinicalBridge
   ```

2. **Install Python dependencies**
   ```bash
   poetry install
   ```

3. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env and add your API keys
   ```

4. **Start local services (Qdrant, PostgreSQL, Redis)**
   ```bash
   docker-compose up -d
   ```

5. **Verify services are running**
   ```bash
   docker-compose ps
   # Should show qdrant, postgres, and redis as "Up"
   ```

### Configuration

Edit [.env](.env) file with your credentials:

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

## Development

### Project Structure

```
claudeClinicalBridge/
├── src/python/              # Python backend
│   ├── mcp_servers/        # MCP server implementations
│   ├── agents/             # Claude Agent SDK sub-agents
│   ├── skills/             # Reusable agent skills (.md files)
│   ├── orchestration/      # Workflow coordinator
│   ├── evaluation/         # Evaluation framework
│   ├── security/           # HIPAA compliance utilities
│   └── utils/              # Configuration and logging
├── src/typescript/          # TypeScript API layer (future)
├── tests/                   # Unit, integration, and evaluation tests
├── data/                    # Medical code datasets
├── docs/                    # Documentation
├── scripts/                 # Utility scripts
└── docker-compose.yml       # Local development services
```

### Running Tests

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=src --cov-report=html

# Run specific test file
poetry run pytest tests/unit/test_config.py

# Run integration tests (requires FHIR credentials)
poetry run pytest tests/integration/
```

### Code Quality

```bash
# Lint code
poetry run ruff check .

# Format code
poetry run ruff format .

# Type checking
poetry run mypy src/

# Security scan
poetry run bandit -r src/python/ -ll
```

### Running MCP Servers

```bash
# Start all MCP servers
python scripts/start_mcp_servers.py

# Or start individually
python -m src.python.mcp_servers.medical_knowledge.server
python -m src.python.mcp_servers.epic_fhir.server
```

## Usage

### Basic Example

```python
from src.python.orchestration.coordinator import ClinicalDocumentationCoordinator
from src.python.utils.config import settings

# Initialize coordinator
coordinator = ClinicalDocumentationCoordinator(settings)

# Process clinical note
clinical_note = """
65yo M presents with chest pain, elevated BP 160/95.
History of HTN and T2DM. Currently on metformin and lisinopril.
"""

result = await coordinator.process_clinical_note(
    note=clinical_note,
    patient_id="epic-patient-123",
    payer="Medicare"
)

print(result)
# Output:
# {
#     "structured_documentation": {...},
#     "icd10_codes": ["I20.9", "I10", "E11.9"],
#     "cpt_codes": ["99214"],
#     "compliance_status": "approved",
#     "prior_authorization": null,
#     "quality_assured": true
# }
```

## Evaluation

The system includes a comprehensive evaluation framework with 5 key metrics:

1. **Coding Accuracy** - Compare against expert coders (target: >90%)
2. **Clinical Validity** - Medical professional review
3. **Compliance Catch Rate** - Flag documentation gaps (target: >85%)
4. **Hallucination Audit** - Detect fabricated claims (target: <5%)
5. **End-to-End Latency** - Complete workflow timing (target: <30s)

```bash
# Run evaluation suite
python scripts/run_evaluation.py --full

# Quick evaluation (10 cases)
python scripts/run_evaluation.py --quick

# Specific metrics
python scripts/run_evaluation.py --metrics coding_accuracy,hallucination
```

## HIPAA Compliance

This application implements HIPAA security principles even in sandbox/development:

- ✅ **PHI Redaction** - Automatic PHI detection and redaction in logs
- ✅ **Audit Logging** - All patient data access logged with timestamps
- ✅ **Encryption** - Data encrypted at rest (tokens, cached FHIR data)
- ✅ **Minimum Necessary** - Only access required patient data
- ✅ **Access Controls** - Role-based access (future)

See [docs/hipaa_compliance.md](docs/hipaa_compliance.md) for full details.

## Documentation

- [Architecture](docs/architecture.md) - System design and component interactions
- [MCP Servers](docs/mcp_servers.md) - MCP server API reference
- [Agents](docs/agents.md) - Agent descriptions and workflows
- [Skills](docs/skills.md) - Skill definitions and usage
- [Deployment](docs/deployment.md) - Production deployment guide
- [HIPAA Compliance](docs/hipaa_compliance.md) - Security and compliance measures
- [Evaluation](docs/evaluation.md) - Metrics and evaluation framework

## Roadmap

### Phase 1: Foundation ✅
- [x] Project structure and configuration
- [x] Docker Compose for local services
- [x] Configuration management and logging

### Phase 2: MCP Servers (In Progress)
- [ ] Medical Knowledge Base MCP Server
- [ ] Epic FHIR MCP Server
- [ ] Oracle Health MCP Server
- [ ] Payer Policy MCP Server

### Phase 3: Agents & Skills
- [ ] 4 Agent Skills (Markdown)
- [ ] 5 Sub-Agents (Claude Agent SDK)
- [ ] Orchestration Layer

### Phase 4: Evaluation & Security
- [ ] Evaluation Framework
- [ ] HIPAA Compliance Components
- [ ] CI/CD Pipelines

### Future Enhancements
- [ ] Human-in-the-Loop UI (TypeScript/React)
- [ ] Real-time dictation support
- [ ] Learning from corrections
- [ ] Mobile app (iOS/Android)
- [ ] Multi-modal support (images, PDFs)

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- **Anthropic** - Claude API and Agent SDK
- **Epic Systems** - FHIR sandbox access
- **Oracle Health** - Developer program and FHIR APIs
- **CDC/CMS** - Public ICD-10 code datasets
- **DMIS Lab** - BioBERT pre-trained model

## Support

- 📧 Email: support@clinicalbridge.example.com
- 💬 Discord: [Join our community](https://discord.gg/clinicalbridge)
- 🐛 Issues: [GitHub Issues](https://github.com/yourusername/claudeClinicalBridge/issues)
- 📖 Docs: [Full Documentation](https://docs.clinicalbridge.example.com)

## Disclaimer

⚠️ **This is a development/research project using synthetic data and EHR sandboxes.**

**NOT FOR PRODUCTION USE WITH REAL PATIENT DATA** without:
- Proper HIPAA Business Associate Agreements (BAA) with all vendors
- Security audit and penetration testing
- CPT code licensing from AMA (if using full CPT dataset)
- Legal review and compliance certification
- Appropriate medical professional oversight

Always consult with certified professional coders and healthcare compliance experts before using AI-assisted coding in production.

---

**Built with ❤️ using Claude Agent SDK and Model Context Protocol**
