# Oracle Health (Cerner) FHIR Setup Guide

Complete guide to setting up Oracle Health (Cerner) FHIR integration with SMART on FHIR authentication.

---

## Overview

This MCP server integrates with Oracle Health's (formerly Cerner) FHIR R4 APIs using SMART on FHIR Backend Services authentication. It provides 7 tools for querying patient data:

- **search_patients** - Search for patients by name, DOB, or identifier
- **get_patient** - Retrieve patient demographics by ID
- **get_patient_encounters** - Fetch patient encounters (visits)
- **get_patient_conditions** - Retrieve problem list and diagnoses
- **get_patient_observations** - Get lab results and vitals
- **get_patient_medications** - Retrieve medication list
- **get_patient_everything** - Comprehensive patient data retrieval

---

## Prerequisites

1. **Oracle Health Developer Account**
   - Sign up at [Oracle Health Developer Portal](https://developer.oraclehealth.com/)
   - Access to Ignite FHIR sandbox

2. **Python Environment**
   ```bash
   poetry install
   ```

3. **RSA Key Pair** (for JWT signing)
   - Private key (PEM format) for your application
   - Public key (JWK format) registered with Oracle Health

---

## Step 1: Register Application with Oracle Health

### 1.1 Access Developer Portal

1. Go to [Oracle Health Developer Portal](https://developer.oraclehealth.com/)
2. Sign in or create an account
3. Navigate to "My Apps" or "Applications"

### 1.2 Create New Application

1. Click "Create Application" or "Register App"
2. Fill in application details:
   - **App Name**: Claude Clinical Bridge (or your app name)
   - **Description**: AI-powered clinical documentation assistant
   - **App Type**: Backend Service / System Account
   - **FHIR Version**: R4

### 1.3 Configure SMART on FHIR

1. **Grant Type**: Select "Client Credentials"
2. **Authentication Method**: Select "Private Key JWT"
3. **Scopes**: Request the following scopes:
   - `system/Patient.read`
   - `system/Encounter.read`
   - `system/Condition.read`
   - `system/Observation.read`
   - `system/MedicationRequest.read`
   - `system/*.read` (if available for broader access)

### 1.4 Get Client Credentials

After registration, you'll receive:
- **Client ID**: Your application's unique identifier (e.g., `a1b2c3d4-5678-90ab-cdef-1234567890ab`)
- **Tenant ID**: Oracle Health tenant identifier
- **FHIR Base URL**: Sandbox FHIR endpoint (e.g., `https://fhir-ehr-code.cerner.com/r4/ec2458f2-1e24-41c8-b71b-0e701af7583d`)
- **Token URL**: OAuth token endpoint (e.g., `https://authorization.cerner.com/tenants/{tenant_id}/protocols/oauth2/profiles/smart-v1/token`)

---

## Step 2: Generate RSA Key Pair

### 2.1 Generate Private Key

```bash
# Generate 2048-bit RSA private key
openssl genrsa -out oracle_private_key.pem 2048

# Verify key format
openssl rsa -in oracle_private_key.pem -check -noout
```

**Output:**
```
Generating RSA private key, 2048 bit long modulus
...
e is 65537 (0x10001)
```

### 2.2 Generate Public Key (PEM format)

```bash
# Extract public key
openssl rsa -in oracle_private_key.pem -pubout -out oracle_public_key.pem

# View public key
cat oracle_public_key.pem
```

### 2.3 Convert Public Key to JWK Format

Oracle Health requires the public key in JSON Web Key (JWK) format.

**Option A: Use Python Script**

```python
# scripts/convert_pem_to_jwk.py
import json
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.serialization import load_pem_public_key
import base64

# Load public key
with open("oracle_public_key.pem", "rb") as f:
    public_key = load_pem_public_key(f.read(), backend=default_backend())

# Get public numbers
public_numbers = public_key.public_numbers()

# Convert to base64url
def int_to_base64url(num):
    num_bytes = num.to_bytes((num.bit_length() + 7) // 8, byteorder='big')
    return base64.urlsafe_b64encode(num_bytes).rstrip(b'=').decode('utf-8')

jwk = {
    "kty": "RSA",
    "use": "sig",
    "alg": "RS384",
    "n": int_to_base64url(public_numbers.n),
    "e": int_to_base64url(public_numbers.e),
}

print(json.dumps(jwk, indent=2))
```

Run:
```bash
python scripts/convert_pem_to_jwk.py > oracle_public_key.jwk
```

**Option B: Use Online Tool**
- https://irrte.ch/jwt-js-decode/pem2jwk.html
- Upload `oracle_public_key.pem`
- Copy the JWK output

### 2.4 Register Public Key with Oracle Health

1. In Oracle Health Developer Portal, go to your application
2. Navigate to "Keys" or "Authentication" section
3. Click "Add Public Key"
4. Paste the JWK JSON content
5. Save the key

---

## Step 3: Configure Environment Variables

Create or update `.env` file:

```bash
# Oracle Health (Cerner) FHIR Configuration
ORACLE_CLIENT_ID=your-oracle-client-id-here
ORACLE_FHIR_BASE_URL=https://fhir-ehr-code.cerner.com/r4/your-tenant-id
ORACLE_AUTH_URL=https://authorization.cerner.com/tenants/your-tenant-id/protocols/oauth2/profiles/smart-v1/token
ORACLE_PRIVATE_KEY_PATH=/path/to/oracle_private_key.pem

# Anthropic API Key
ANTHROPIC_API_KEY=your-anthropic-api-key
```

**Important**: Replace placeholders with your actual values:
- `your-oracle-client-id-here` → Your Client ID from Step 1.4
- `your-tenant-id` → Your Oracle Health tenant ID
- `/path/to/oracle_private_key.pem` → Absolute path to your private key

---

## Step 4: Test Authentication

### 4.1 Test JWT Generation

```python
# scripts/test_oracle_jwt.py
import asyncio
from src.python.mcp_servers.oracle_fhir.client import OracleHealthFHIRClient

async def test_jwt():
    client = OracleHealthFHIRClient()
    jwt_token = client._generate_jwt_assertion()
    print(f"JWT Token: {jwt_token[:50]}...")
    print("JWT generation successful!")
    await client.close()

asyncio.run(test_jwt())
```

Run:
```bash
python scripts/test_oracle_jwt.py
```

Expected output:
```
JWT Token: eyJhbGciOiJSUzM4NCIsInR5cCI6IkpXVCJ9.eyJpc3MiOi...
JWT generation successful!
```

### 4.2 Test Authentication Flow

```python
# scripts/test_oracle_auth.py
import asyncio
from src.python.mcp_servers.oracle_fhir.client import OracleHealthFHIRClient

async def test_auth():
    client = OracleHealthFHIRClient()
    try:
        token = await client.authenticate()
        print(f"✓ Authentication successful!")
        print(f"  Token: {token[:20]}...")
        print(f"  Expires: {client._token_expiry}")
    except Exception as e:
        print(f"✗ Authentication failed: {e}")
    finally:
        await client.close()

asyncio.run(test_auth())
```

Run:
```bash
python scripts/test_oracle_auth.py
```

Expected output:
```
✓ Authentication successful!
  Token: eyJhbGciOiJSUzM4NCIsInR5cCI6IkpXVCJ9.eyJzdWI...
  Expires: 2026-02-16 15:45:30.123456
```

---

## Step 5: Test FHIR Operations

### 5.1 Test Patient Search

```python
# scripts/test_oracle_patient.py
import asyncio
from src.python.mcp_servers.oracle_fhir.client import OracleHealthFHIRClient

async def test_patient_search():
    client = OracleHealthFHIRClient()
    try:
        # Search for patients by name
        patients = await client.search_patients(family="Smith", limit=5)
        print(f"✓ Found {len(patients)} patients")
        for patient in patients:
            print(f"  - {patient.id}: {patient.name[0].text}")
    except Exception as e:
        print(f"✗ Patient search failed: {e}")
    finally:
        await client.close()

asyncio.run(test_patient_search())
```

### 5.2 Test Patient Retrieval

```python
import asyncio
from src.python.mcp_servers.oracle_fhir.client import OracleHealthFHIRClient

async def test_patient_get():
    client = OracleHealthFHIRClient()
    try:
        # Replace with a valid patient ID from your sandbox
        patient = await client.get_patient("12724066")

        print(f"✓ Patient Retrieved:")
        print(f"  ID: {patient.id}")
        print(f"  Name: {patient.name[0].text if patient.name else 'N/A'}")
        print(f"  DOB: {patient.birthDate}")
        print(f"  Gender: {patient.gender}")
    except Exception as e:
        print(f"✗ Patient retrieval failed: {e}")
    finally:
        await client.close()

asyncio.run(test_patient_get())
```

---

## Step 6: Run Unit Tests

```bash
# Run Oracle Health FHIR tests
pytest tests/unit/test_mcp_servers/test_oracle_fhir.py -v

# Expected output:
# ============================= test session starts ==============================
# tests/unit/test_mcp_servers/test_oracle_fhir.py::TestOracleHealthFHIRClient::test_client_initialization PASSED
# tests/unit/test_mcp_servers/test_oracle_fhir.py::TestOracleHealthFHIRClient::test_jwt_generation PASSED
# tests/unit/test_mcp_servers/test_oracle_fhir.py::TestOracleHealthFHIRClient::test_authentication_success PASSED
# ...
# ============================= 14 passed in 2.35s ==========================================
```

---

## Step 7: Use MCP Server

### 7.1 Start MCP Server

```python
# scripts/start_oracle_mcp.py
import asyncio
from src.python.mcp_servers.oracle_fhir.server import mcp

if __name__ == "__main__":
    mcp.run()
```

### 7.2 Use MCP Tools

```python
from src.python.mcp_servers.oracle_fhir.server import search_patients, get_patient

# Search for patients
patients = await search_patients(family="Johnson", given="Jane", limit=10)

# Get specific patient
patient = await get_patient("12724066")

# Get patient conditions
conditions = await get_patient_conditions("12724066", clinical_status="active")

# Get everything for a patient
everything = await get_patient_everything("12724066")
```

---

## Troubleshooting

### Issue: "401 Unauthorized" Error

**Cause**: Invalid JWT or client credentials

**Solutions**:
1. Verify Client ID matches registered app
2. Check private key is correct PEM format
3. Verify public key is registered in Oracle Health portal
4. Ensure token URL is correct for your tenant
5. Check system clock is synchronized (JWT timestamps)

```bash
# Verify JWT claims
python -c "
import jwt
token = 'YOUR_JWT_HERE'
print(jwt.decode(token, options={'verify_signature': False}))
"
```

### Issue: "403 Forbidden" Error

**Cause**: Missing or insufficient scopes

**Solutions**:
1. Check requested scopes in Oracle Health app settings
2. Ensure `system/Patient.read`, `system/Encounter.read`, etc. are granted
3. Re-authenticate after scope changes

### Issue: "404 Not Found" for Patient

**Cause**: Patient ID doesn't exist in sandbox

**Solutions**:
1. Use Oracle Health sandbox test patient IDs
2. Check tenant ID in FHIR base URL is correct
3. Verify you're querying the correct environment (sandbox vs production)

**Oracle Health Test Patient IDs:**
- `12724066` - Smart, Nancy
- `12742400` - Smart, Joe
- `12742401` - Smart, Timmy

### Issue: "Private key not found" Error

**Cause**: Invalid private key path

**Solutions**:
1. Use absolute path: `/home/user/keys/oracle_private_key.pem`
2. Check file permissions: `chmod 600 oracle_private_key.pem`
3. Verify file exists: `ls -la /path/to/oracle_private_key.pem`

### Issue: JWT Signature Verification Failed

**Cause**: Public/private key mismatch

**Solutions**:
1. Regenerate key pair and re-register public key
2. Ensure using RS384 algorithm (not RS256)
3. Verify JWK conversion is correct

---

## Security Best Practices

### 1. Protect Private Key
```bash
# Set restrictive permissions
chmod 600 oracle_private_key.pem

# Never commit to git
echo "oracle_private_key.pem" >> .gitignore
```

### 2. Use Environment Variables
Never hardcode credentials in source code. Always use `.env` files or secure secret management.

### 3. Rotate Keys Regularly
- Generate new key pairs every 90 days
- Update public key in Oracle Health portal
- Maintain key version history for audit

### 4. Monitor Access Logs
- Review OAuth token requests
- Track API usage patterns
- Alert on anomalous access

---

## Oracle Health FHIR Resources

### Official Documentation
- [Oracle Health Developer Portal](https://developer.oraclehealth.com/)
- [Ignite FHIR R4 APIs](https://docs.oraclehealth.com/fhir/r4/)
- [SMART on FHIR Backend Services](https://docs.oraclehealth.com/fhir/authorization/)

### FHIR Specifications
- [FHIR R4 Specification](https://hl7.org/fhir/R4/)
- [SMART App Launch](http://hl7.org/fhir/smart-app-launch/)
- [SMART Backend Services](http://hl7.org/fhir/smart-app-launch/backend-services.html)

### Sample Code
- [Oracle Health FHIR Examples](https://github.com/cerner/fhir.cerner.com)

---

## Next Steps

1. ✅ Complete Oracle Health setup
2. ✅ Test all MCP tools
3. ⏭️ Move to Phase 4: Payer Policy MCP Server
4. ⏭️ Implement agent skills and sub-agents
5. ⏭️ Create orchestration layer

---

## Support

For Oracle Health-specific issues:
- **Developer Forum**: https://developer.oraclehealth.com/forum
- **Support Email**: developer-support@oraclehealth.com
- **Sandbox Status**: Check status page for known issues

For this implementation:
- Open an issue on GitHub
- Check existing documentation
- Review test files for examples
