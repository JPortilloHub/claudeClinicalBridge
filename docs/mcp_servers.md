# MCP Servers API Reference

This document describes the four Model Context Protocol (MCP) servers that provide tools for the agent pipeline.

## Overview

| Server | Name | Transport | Purpose |
|--------|------|-----------|---------|
| Epic FHIR | `epic-fhir` | stdio | Patient data from Epic EHR sandbox |
| Oracle Health | `oracle-health` | stdio | Patient data from Oracle Health/Cerner sandbox |
| Medical Knowledge | `medical-knowledge` | stdio | Semantic search over ICD-10/CPT codes |
| Payer Policy | `payer-policy` | stdio | Prior auth and documentation requirements |

All servers use `FastMCP` from the MCP SDK and support lazy, thread-safe client initialization.

---

## Epic FHIR MCP Server

**Location**: `src/python/mcp_servers/epic_fhir/server.py`

Integrates with Epic's FHIR R4 sandbox via SMART on FHIR Backend Services (JWT-based OAuth).

### Tools

#### `search_patients`
Search for patients by name, DOB, or identifier.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `family` | `str \| None` | `None` | Family (last) name |
| `given` | `str \| None` | `None` | Given (first) name |
| `birthdate` | `str \| None` | `None` | Birth date (YYYY-MM-DD) |
| `identifier` | `str \| None` | `None` | Patient identifier (MRN) |
| `limit` | `int` | `10` | Max results (max: 50) |

**Returns**: List of patient demographics (id, name, birthDate, gender, address).

#### `get_patient`
Retrieve patient demographics by FHIR Patient ID.

| Parameter | Type | Description |
|-----------|------|-------------|
| `patient_id` | `str` | FHIR Patient ID |

**Returns**: Patient resource (demographics, identifiers, contact info).

#### `get_patient_encounters`
Fetch patient encounters with optional date filtering.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `patient_id` | `str` | - | FHIR Patient ID |
| `date_from` | `str \| None` | `None` | Start date (YYYY-MM-DD) |
| `date_to` | `str \| None` | `None` | End date (YYYY-MM-DD) |
| `limit` | `int` | `20` | Max results |

#### `get_patient_conditions`
Retrieve problem list and diagnoses.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `patient_id` | `str` | - | FHIR Patient ID |
| `clinical_status` | `str \| None` | `None` | Filter: active, resolved, inactive |

#### `get_patient_observations`
Fetch lab results and vitals.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `patient_id` | `str` | - | FHIR Patient ID |
| `category` | `str \| None` | `None` | laboratory, vital-signs, social-history |
| `limit` | `int` | `50` | Max results |

#### `get_patient_medications`
Retrieve active medication orders.

| Parameter | Type | Description |
|-----------|------|-------------|
| `patient_id` | `str` | FHIR Patient ID |

#### `get_patient_everything`
Comprehensive patient data bundle (demographics + encounters + conditions + observations + medications).

| Parameter | Type | Description |
|-----------|------|-------------|
| `patient_id` | `str` | FHIR Patient ID |

### Resources

- `epic://patient/{patient_id}` - Patient resource lookup

### Configuration

| Environment Variable | Description |
|---------------------|-------------|
| `EPIC_BASE_URL` | Epic FHIR base URL |
| `EPIC_CLIENT_ID` | SMART on FHIR client ID |
| `EPIC_CLIENT_SECRET` | SMART on FHIR client secret |
| `EPIC_TOKEN_URL` | OAuth token endpoint |

---

## Oracle Health MCP Server

**Location**: `src/python/mcp_servers/oracle_fhir/server.py`

Integrates with Oracle Health (Cerner) Ignite FHIR R4 APIs. Exposes the same tool interface as the Epic server for EHR-agnostic agent design.

### Tools

Same interface as Epic FHIR server:
- `search_patients`
- `get_patient`
- `get_patient_encounters`
- `get_patient_conditions`
- `get_patient_observations`
- `get_patient_medications`
- `get_patient_everything`

### Configuration

| Environment Variable | Description |
|---------------------|-------------|
| `ORACLE_BASE_URL` | Oracle Health FHIR base URL |
| `ORACLE_CLIENT_ID` | OAuth client ID |
| `ORACLE_CLIENT_SECRET` | OAuth client secret |
| `ORACLE_TOKEN_URL` | OAuth token endpoint |

---

## Medical Knowledge MCP Server

**Location**: `src/python/mcp_servers/medical_knowledge/server.py`

Provides semantic search over ICD-10-CM and CPT codes using BioBERT embeddings stored in Qdrant vector database.

### Tools

#### `search_icd10`
Search ICD-10-CM diagnosis codes by clinical description.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `query` | `str` | - | Natural language description (e.g., "high blood sugar") |
| `limit` | `int` | `10` | Max results (max: 50) |
| `similarity_threshold` | `float` | `0.7` | Minimum similarity score (0-1) |

**Returns**: List of `{code, description, category, similarity_score}`.

#### `search_cpt`
Search CPT procedure codes by description.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `query` | `str` | - | Procedure description (e.g., "knee replacement") |
| `limit` | `int` | `10` | Max results |
| `similarity_threshold` | `float` | `0.7` | Minimum similarity score |

#### `get_code_details`
Get full details for a specific code.

| Parameter | Type | Description |
|-----------|------|-------------|
| `code_type` | `str` | `"icd10"` or `"cpt"` |
| `code` | `str` | Code value (e.g., `"I10"`, `"99214"`) |

#### `get_code_hierarchy`
Get parent/child code relationships.

| Parameter | Type | Description |
|-----------|------|-------------|
| `code_type` | `str` | `"icd10"` or `"cpt"` |
| `code` | `str` | Code value |

### Resources

- `code://{code_type}/{code}` - Individual code lookup

### Configuration

| Environment Variable | Description |
|---------------------|-------------|
| `QDRANT_URL` | Qdrant vector database URL |
| `QDRANT_API_KEY` | Qdrant API key (optional for local) |

---

## Payer Policy MCP Server

**Location**: `src/python/mcp_servers/payer_policy/server.py`

Provides prior authorization criteria, documentation requirements, and medical necessity validation from a SQLite-backed policy store.

### Tools

#### `check_auth_requirements`
Check if a procedure requires prior authorization.

| Parameter | Type | Description |
|-----------|------|-------------|
| `payer` | `str` | Payer name (e.g., "Medicare", "UnitedHealthcare") |
| `cpt_code` | `str` | CPT procedure code |

**Returns**: `{requires_prior_auth, prior_auth_criteria, payer, cpt_code, procedure_name}`.

#### `get_documentation_requirements`
Get required documentation elements for a payer/code combination.

| Parameter | Type | Description |
|-----------|------|-------------|
| `payer` | `str` | Payer name |
| `cpt_code` | `str` | CPT code |

**Returns**: `{requirements, payer, cpt_code, procedure_name}`.

#### `validate_medical_necessity`
Validate medical necessity criteria against clinical data.

| Parameter | Type | Description |
|-----------|------|-------------|
| `payer` | `str` | Payer name |
| `cpt_code` | `str` | CPT code |
| `clinical_data` | `dict` | Clinical data with `diagnoses`, `symptoms`, `clinical_notes` keys |

**Returns**: `{is_medically_necessary, criteria_met, criteria_not_met, score}`.

### Data Source

Policy data is stored in `data/policies/policies.json` and loaded into a SQLite database at initialization. The `PolicyStore` class handles querying and caching.
