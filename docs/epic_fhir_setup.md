## Epic FHIR Integration Setup Guide

This guide explains how to set up Epic FHIR integration for the Clinical Bridge application using SMART on FHIR Backend Services authentication.

---

## Overview

The Epic FHIR MCP Server enables LLM agents to query Epic EHR systems for patient data including:
- Patient demographics
- Clinical encounters
- Diagnoses (conditions)
- Laboratory results and vitals (observations)
- Medication orders

Authentication uses **SMART on FHIR Backend Services** (OAuth 2.0 client_credentials grant with JWT assertion).

---

## Prerequisites

- Epic Sandbox account (free for development)
- OpenSSL for generating RSA key pair
- Python 3.10+ with dependencies installed

---

## Step 1: Register Epic Sandbox App

### 1.1 Create Epic Account

1. Go to [Epic FHIR Sandbox](https://fhir.epic.com/)
2. Click "Build Apps" → "Get Sandbox Credentials"
3. Create an account or sign in
4. Complete the registration form

### 1.2 Register Non-Production Application

1. Navigate to "App Gallery" → "Create"
2. Fill in application details:
   - **Application Name**: "Clinical Bridge" (or your app name)
   - **Application Type**: Backend System
   - **FHIR Version**: R4
   - **OAuth Grant Type**: Backend Services (Client Credentials)

3. Select required scopes:
   ```
   system/Patient.read
   system/Encounter.read
   system/Condition.read
   system/Observation.read
   system/MedicationRequest.read
   ```

4. **IMPORTANT**: Note your **Client ID** (looks like `abc123-def456-...`)

---

## Step 2: Generate RSA Key Pair

Epic requires RS384 algorithm for JWT signing. Generate a 4096-bit RSA key pair:

### 2.1 Generate Private Key

```bash
# Create config directory
mkdir -p /workspaces/claudeClinicalBridge/config

# Generate private key
openssl genrsa -out /workspaces/claudeClinicalBridge/config/epic_private_key.pem 4096

# Verify key was created
ls -lh /workspaces/claudeClinicalBridge/config/epic_private_key.pem
```

**Security Note**: Keep this private key secure! Add to `.gitignore` (already configured).

### 2.2 Generate Public Key

```bash
# Extract public key from private key
openssl rsa -in /workspaces/claudeClinicalBridge/config/epic_private_key.pem \
            -pubout \
            -out /workspaces/claudeClinicalBridge/config/epic_public_key.pem
```

### 2.3 Generate JWK (JSON Web Key)

Epic requires the public key in JWK format:

```bash
# Install jwcrypto if not already installed
pip install jwcrypto

# Convert PEM to JWK
python -c "
from jwcrypto import jwk
import json

with open('/workspaces/claudeClinicalBridge/config/epic_public_key.pem', 'rb') as f:
    key = jwk.JWK.from_pem(f.read())

# Export as JWK
jwk_data = json.loads(key.export_public())
jwk_data['kid'] = 'my-key-id'  # Key ID (you choose this)
jwk_data['use'] = 'sig'  # Signature use
jwk_data['alg'] = 'RS384'  # Algorithm

# Create JWKS (JWK Set)
jwks = {'keys': [jwk_data]}

print(json.dumps(jwks, indent=2))
" > /workspaces/claudeClinicalBridge/config/epic_jwks.json
```

---

## Step 3: Upload Public Key to Epic

### 3.1 Copy JWK Content

```bash
cat /workspaces/claudeClinicalBridge/config/epic_jwks.json
```

### 3.2 Add to Epic App

1. Go to Epic App Gallery → Your App → Edit
2. Scroll to "Public Key" section
3. Select "JWKS" format
4. Paste the content from `epic_jwks.json`
5. Save changes

---

## Step 4: Configure Environment Variables

### 4.1 Create .env File

```bash
cp .env.example .env
```

### 4.2 Edit .env File

Update the following Epic-specific variables:

```bash
# Epic FHIR Configuration
EPIC_CLIENT_ID=your-client-id-from-epic-app-gallery
EPIC_PRIVATE_KEY_PATH=./config/epic_private_key.pem

# Epic Sandbox URLs (these are correct for sandbox)
EPIC_FHIR_BASE_URL=https://fhir.epic.com/interconnect-fhir-oauth/api/FHIR/R4
EPIC_AUTH_URL=https://fhir.epic.com/interconnect-fhir-oauth/oauth2/token
```

**Production URLs** (when ready):
```bash
# Your production Epic FHIR endpoints (provided by Epic)
EPIC_FHIR_BASE_URL=https://your-epic-instance.com/interconnect-fhir-oauth/api/FHIR/R4
EPIC_AUTH_URL=https://your-epic-instance.com/interconnect-fhir-oauth/oauth2/token
```

---

## Step 5: Test Configuration

### 5.1 Run Unit Tests

```bash
# Run Epic FHIR tests
pytest tests/unit/test_mcp_servers/test_epic_fhir.py -v

# Expected output:
# ✓ test_client_initialization PASSED
# ✓ test_jwt_generation PASSED
# ✓ test_authentication_success PASSED
# ...
```

### 5.2 Test Authentication

Create a test script:

```python
# test_epic_auth.py
import asyncio
from src.python.mcp_servers.epic_fhir.client import EpicFHIRClient

async def test_auth():
    async with EpicFHIRClient() as client:
        try:
            token = await client.authenticate()
            print(f"✓ Authentication successful!")
            print(f"  Token: {token[:20]}...")
        except Exception as e:
            print(f"✗ Authentication failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_auth())
```

Run it:
```bash
python test_epic_auth.py
```

### 5.3 Test Patient Search

Use Epic's sandbox test patient IDs:

```python
# test_epic_patient.py
import asyncio
from src.python.mcp_servers.epic_fhir.client import EpicFHIRClient

async def test_patient():
    async with EpicFHIRClient() as client:
        try:
            # Epic sandbox test patient ID
            patient_id = "erXuFYUfucBZaryVksYEcMg3"

            patient = await client.get_patient(patient_id)
            print(f"✓ Patient retrieved!")
            print(f"  ID: {patient.id}")
            print(f"  Name: {patient.name[0].text if patient.name else 'N/A'}")
            print(f"  DOB: {patient.birthDate}")
            print(f"  Gender: {patient.gender}")

        except Exception as e:
            print(f"✗ Failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_patient())
```

---

## Step 6: Start MCP Server

### 6.1 Run Server

```bash
python -m src.python.mcp_servers.epic_fhir.server
```

### 6.2 Test MCP Tools

The server exposes these tools to LLM agents:
- `search_patients`
- `get_patient`
- `get_patient_encounters`
- `get_patient_conditions`
- `get_patient_observations`
- `get_patient_medications`
- `get_patient_everything`

---

## Epic Sandbox Test Patient IDs

Epic provides test patient IDs for development:

| Patient ID | Name | Description |
|------------|------|-------------|
| `erXuFYUfucBZaryVksYEcMg3` | Jason Argonaut | Complete test data |
| `eq081-VQEgP8drUUqCWzHfw3` | Jessica Argonaut | Pregnancy data |
| `eM0-PQh7pAZjrMCnVNXYEMw3` | Timothy Bixby | Pediatric data |

**Search by MRN**:
```bash
MRN: E3437
```

---

## Troubleshooting

### Authentication Fails

**Error**: `401 Unauthorized` or `invalid_client`

**Solutions**:
1. Verify Client ID is correct
2. Check JWK was uploaded correctly to Epic
3. Ensure private key matches public key:
   ```bash
   # Verify keys match
   openssl rsa -in config/epic_private_key.pem -pubout | \
   diff - config/epic_public_key.pem
   ```

### JWT Signature Invalid

**Error**: `invalid_grant` or `signature verification failed`

**Solutions**:
1. Verify RS384 algorithm is used (not RS256)
2. Check key ID (kid) matches between JWKS and JWT
3. Ensure clock is synchronized (JWT exp/iat times)

### Patient Not Found

**Error**: `404 Not Found` for patient

**Solutions**:
1. Use Epic sandbox test patient IDs (see table above)
2. Verify patient ID format (Epic uses format like `abc123.xyz789`)
3. Check scopes include `system/Patient.read`

### Rate Limiting

**Error**: `429 Too Many Requests`

**Solutions**:
1. Epic sandbox has rate limits (50 requests/minute)
2. Implement exponential backoff
3. Cache patient data when possible

---

## Security Best Practices

### Production Deployment

1. **Private Key Storage**:
   ```bash
   # Use environment-specific key management
   # AWS: Secrets Manager
   # Azure: Key Vault
   # GCP: Secret Manager
   ```

2. **Rotate Keys Regularly**:
   - Generate new key pair every 90 days
   - Update JWKS in Epic
   - Deploy new private key

3. **Audit Logging**:
   - Log all FHIR API calls
   - Monitor for unusual access patterns
   - Alert on authentication failures

4. **Network Security**:
   - Use HTTPS only
   - Whitelist Epic IP ranges
   - Implement request signing

### HIPAA Compliance

1. **Data Encryption**:
   - TLS 1.2+ for transport
   - Encrypt data at rest
   - Use encrypted backups

2. **Access Controls**:
   - Implement role-based access
   - Audit trail for PHI access
   - Regular access reviews

3. **PHI Handling**:
   - Minimize PHI in logs
   - Redact PHI in error messages
   - Secure PHI disposal

---

## Epic FHIR Resources

- [Epic FHIR Documentation](https://fhir.epic.com/Documentation)
- [SMART on FHIR Backend Services](https://hl7.org/fhir/smart-app-launch/backend-services.html)
- [Epic App Gallery](https://appmarket.epic.com/)
- [FHIR R4 Specification](https://hl7.org/fhir/R4/)

---

## Support

For Epic-specific issues:
- Epic Developer Forum: https://galaxy.epic.com/
- Epic Support: https://userweb.epic.com/

For Clinical Bridge issues:
- GitHub Issues: https://github.com/your-org/claude-clinical-bridge/issues

---

**Next Steps**: After Epic is working, set up [Oracle Health FHIR Integration](oracle_fhir_setup.md)
