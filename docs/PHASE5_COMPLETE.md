# Phase 5: Agent Skills - Complete

## Overview

Phase 5 implements 4 Markdown-based agent skills and a skill loader module. These skills provide domain-specific knowledge and reasoning frameworks that Phase 6's Claude sub-agents will reference as system prompt content.

## Architecture

```
src/python/skills/
├── __init__.py                        # Package exports
├── skill_loader.py                    # Skill loading and combination utilities
├── medical_terminology_skill.md       # Precise medical language
├── coding_accuracy_skill.md           # ICD-10/CPT code selection rules
├── clinical_reasoning_skill.md        # Differential diagnosis reasoning
└── regulatory_compliance_skill.md     # HIPAA and coding compliance

tests/unit/test_skills/
└── test_skill_loader.py               # 21 unit tests (all passing)
```

## Skills

### 1. Medical Terminology Skill
- Converts informal/colloquial physician language to standardized medical terms
- Symptom-to-terminology conversion tables (30+ mappings)
- Temporal and severity descriptors
- Anatomical precision rules
- HPI 8-element coverage
- Review of Systems (ROS) terminology by system
- Common abbreviation expansions

### 2. Coding Accuracy Skill
- ICD-10-CM code structure and specificity requirements
- Laterality rules (1=right, 2=left, 3=bilateral)
- 7th character extensions for injury codes
- Sequencing rules (Code first / Use additional / Excludes1 / Excludes2)
- Combination code guidance
- E/M code selection (2021+ MDM and time-based guidelines)
- CPT modifier usage table
- Common coding errors to avoid (7 categories)
- Validation checklist

### 3. Clinical Reasoning Skill
- Problem representation framework
- Semantic qualifier analysis
- VINDICATE mnemonic for differential generation
- Differential prioritization (life-threatening → most likely → must-not-miss → common)
- Pattern recognition (System 1) with classic presentation tables
- Analytical reasoning (System 2) for complex cases
- SOAP note reasoning structure
- Pertinent positives and negatives documentation
- Cognitive bias awareness (7 biases with mitigations)

### 4. Regulatory Compliance Skill
- HIPAA 18 PHI identifiers (complete table)
- Minimum necessary standard
- PHI handling rules for the system
- Clinical Documentation Integrity (CDI) requirements
- Documentation requirements by visit type
- Compliant provider query process
- CMS fraud and abuse regulations (FCA, AKS, Stark, HIPAA penalties)
- Coding and documentation red flags
- NCCI edit checking
- Audit trail requirements
- Retention requirements

## Skill Loader

The `skill_loader.py` module provides:

| Function | Description |
|----------|-------------|
| `load_skill(name)` | Load a single skill by name |
| `load_skills(*names)` | Load and combine multiple skills |
| `list_available_skills()` | List all available skills with paths |
| `get_skill_summary(name)` | Get title and role description |

### Usage

```python
from src.python.skills import load_skill, load_skills

# Load a single skill for an agent's system prompt
terminology_prompt = load_skill("medical_terminology")

# Combine skills for an agent that needs multiple capabilities
coding_agent_prompt = load_skills("coding_accuracy", "regulatory_compliance")

# List all available skills
from src.python.skills import list_available_skills
skills = list_available_skills()
```

## Test Results

```
21 passed in 0.16s
```

- 4 parametrized tests across all skills
- 4 content-specific tests per skill
- Error handling tests (unknown skills)
- Multi-skill loading and combination tests
- File existence verification

## How Skills Connect to Phase 6 (Sub-Agents)

Each Phase 6 sub-agent will load relevant skills as part of its system prompt:

| Sub-Agent | Skills Used |
|-----------|------------|
| Clinical Documentation Agent | medical_terminology, clinical_reasoning |
| Medical Coding Agent | coding_accuracy, medical_terminology |
| Compliance Agent | regulatory_compliance, coding_accuracy |
| Prior Authorization Agent | regulatory_compliance, clinical_reasoning |
| Quality Assurance Agent | All 4 skills |
