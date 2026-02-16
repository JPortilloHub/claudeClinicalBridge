# HIPAA Compliance

This document describes the HIPAA security safeguards implemented in Claude Clinical Bridge.

## Disclaimer

This project uses **synthetic data and EHR sandboxes only**. Production deployment with real PHI requires:
- Business Associate Agreements (BAA) with Anthropic and all vendors
- Security audit and penetration testing
- Legal review and compliance certification
- Designated Privacy and Security Officers

## Security Components

### 1. PHI Redactor

**Location**: `src/python/security/phi_redactor.py`

Detects and redacts the 18 HIPAA Safe Harbor identifiers from text using pre-compiled regex patterns.

**Detected Categories**:

| Category | Pattern | Example |
|----------|---------|---------|
| SSN | `\d{3}-\d{2}-\d{4}` | 123-45-6789 |
| Phone | `\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}` | (555) 123-4567 |
| Email | Standard email pattern | patient@example.com |
| IP Address | IPv4 format | 192.168.1.100 |
| MRN | `MRN[#:\s-]*\d{4,10}` | MRN: 12345678 |
| Account Number | `ACCT[#:\s-]*\d{4,12}` | ACCT-123456 |
| Date | MM/DD/YYYY, YYYY-MM-DD, Month DD YYYY | 03/15/1985 |
| Age Over 89 | `9\d+ y/o` or similar | 92 y/o |
| ZIP Code | Requires "ZIP" prefix | ZIP 90210 |
| URL | `https?://...` | https://portal.example.com |

**Redaction Methods**:

| Method | Behavior | Example Output |
|--------|----------|----------------|
| `MASK` | Replace with category tag | `[SSN]` |
| `HASH` | Replace with hash prefix | `[SSN:a1b2c3d4]` |
| `REMOVE` | Delete entirely | (empty string) |

**Usage**:
```python
from src.python.security.phi_redactor import redact_phi, RedactionMethod

text = "Patient SSN is 123-45-6789"
redacted, result = redact_phi(text, method=RedactionMethod.MASK)
# redacted == "Patient SSN is [SSN]"
# result.had_phi == True
```

**Dict Redaction**: `redact_dict()` recursively redacts all string values in nested dictionaries.

### 2. Audit Logger

**Location**: `src/python/security/audit_logger.py`

Records all access to patient data in an append-only JSON log file.

**Audit Entry Fields**:

| Field | Description |
|-------|-------------|
| `timestamp` | Unix timestamp |
| `action` | Action performed (see below) |
| `outcome` | success, failure, denied |
| `agent_name` | Agent that performed the action |
| `workflow_id` | Workflow ID for correlation |
| `patient_id_hash` | SHA-256 hash of patient ID (never raw) |
| `resource_type` | Type of resource accessed |
| `detail` | Additional context (must not contain PHI) |

**Audit Actions** (`AuditAction` enum):
- `VIEW` - Viewing patient data
- `CREATE` - Creating new records
- `UPDATE` - Modifying records
- `DELETE` - Deleting records
- `EXPORT` - Exporting data
- `PROCESS` - Pipeline processing
- `CODE_SUGGEST` - Medical code suggestion
- `COMPLIANCE_CHECK` - Compliance validation
- `PRIOR_AUTH` - Prior authorization
- `QA_REVIEW` - Quality assurance review

**Patient ID Hashing**:
Patient IDs are hashed using SHA-256 with a salt derived from the application's secret key. The same patient ID always produces the same hash (for audit correlation), but the hash cannot be reversed to recover the original ID.

```python
def _hash_identifier(identifier: str) -> str:
    salt = settings.secret_key[:16]
    salted = f"{salt}:{identifier}"
    return hashlib.sha256(salted.encode()).hexdigest()[:16]
```

**Querying**: Entries can be queried by action type or workflow ID for compliance audits.

### 3. Encryption Manager

**Location**: `src/python/security/encryption.py`

Encrypts sensitive data at rest (tokens, cached FHIR data, temporary files).

**Primary Method**: Fernet (AES-128-CBC with HMAC-SHA256) via the `cryptography` library.

**Fallback**: HMAC-based XOR obfuscation for environments without `cryptography` installed. This is not cryptographically secure encryption and should only be used for development.

**Key Management**:
- Keys auto-generated on first use
- Stored at configurable path (default: `data/encryption.key`)
- Production should use a key management service (AWS KMS, Azure Key Vault, etc.)

**Usage**:
```python
from src.python.security.encryption import EncryptionManager

manager = EncryptionManager()
ciphertext = manager.encrypt("sensitive data")
plaintext = manager.decrypt(ciphertext)

# Dict support
encrypted = manager.encrypt_dict({"patient_id": "P123", "codes": ["I10"]})
data = manager.decrypt_dict(encrypted)
```

## HIPAA Safeguard Mapping

### Administrative Safeguards

| Requirement | Implementation |
|-------------|---------------|
| Access management | Agent-level access control (each agent only accesses needed tools) |
| Workforce training | Skills contain HIPAA guidelines (regulatory_compliance_skill.md) |
| Audit controls | AuditLogger records all patient data access |
| Incident response | Audit log querying for forensic analysis |

### Technical Safeguards

| Requirement | Implementation |
|-------------|---------------|
| Access control | MCP server authentication (SMART on FHIR OAuth) |
| Audit controls | Append-only structured audit log |
| Integrity controls | Audit entries are append-only, never modified |
| Transmission security | HTTPS for all FHIR API calls |
| Encryption | Fernet encryption for data at rest |

### Data Handling

| Principle | Implementation |
|-----------|---------------|
| Minimum necessary | Agents request only needed FHIR resources |
| PHI in logs | All logs pass through PHI redactor |
| Patient IDs in audit | Hashed with SHA-256 + salt |
| Data retention | Audit logs retained (7-year HIPAA minimum) |
| De-identification | PHI redactor supports Safe Harbor method |

## Security Best Practices

1. **Never log raw PHI** - Use `redact_phi()` or `redact_dict()` before logging
2. **Never store raw patient IDs** - Use `_hash_identifier()` for audit correlation
3. **Encrypt at rest** - Use `EncryptionManager` for cached data and tokens
4. **Audit all access** - Call `AuditLogger.log()` for every patient data operation
5. **Use HTTPS** - All external API calls use TLS
6. **Rotate keys** - Encryption keys should be rotated periodically in production
7. **Restrict access** - Each agent only has access to the MCP tools it needs

## Configuration

| Environment Variable | Description | Default |
|---------------------|-------------|---------|
| `SECRET_KEY` | Application secret for hashing | (insecure default, must set in production) |
| `AUDIT_LOG_PATH` | Path to audit log file | `data/audit.log` |
| `ENCRYPTION_KEY_PATH` | Path to encryption key | `data/encryption.key` |
| `PHI_REDACTION_METHOD` | Default redaction method | `mask` |
| `LOG_LEVEL` | Application log level | `INFO` |
