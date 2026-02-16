"""
Unit tests for HIPAA security components.

Tests cover:
- PHI redactor (pattern detection, redaction methods, dict redaction)
- Audit logger (entry creation, file writing, querying)
- Encryption manager (encrypt/decrypt roundtrip, dict support)
"""

import json
import os
import tempfile

from src.python.security.audit_logger import AuditAction, AuditLogger, AuditOutcome
from src.python.security.encryption import EncryptionManager
from src.python.security.phi_redactor import (
    PHICategory,
    RedactionMethod,
    contains_phi,
    redact_dict,
    redact_phi,
)


# ============================================================================
# PHI Redactor Tests
# ============================================================================


def test_redact_ssn():
    """Test SSN detection and redaction."""
    text = "Patient SSN is 123-45-6789."
    redacted, result = redact_phi(text, method=RedactionMethod.MASK)

    assert "123-45-6789" not in redacted
    assert "[SSN]" in redacted
    assert result.had_phi is True
    assert result.redaction_count >= 1


def test_redact_phone():
    """Test phone number detection."""
    text = "Call patient at (555) 123-4567."
    redacted, result = redact_phi(text, method=RedactionMethod.MASK)

    assert "(555) 123-4567" not in redacted
    assert "[PHONE]" in redacted


def test_redact_email():
    """Test email detection."""
    text = "Send records to patient@example.com."
    redacted, result = redact_phi(text, method=RedactionMethod.MASK)

    assert "patient@example.com" not in redacted
    assert "[EMAIL]" in redacted


def test_redact_ip_address():
    """Test IP address detection."""
    text = "Access from 192.168.1.100."
    redacted, result = redact_phi(text, method=RedactionMethod.MASK)

    assert "192.168.1.100" not in redacted
    assert "[IP_ADDRESS]" in redacted


def test_redact_mrn():
    """Test MRN detection."""
    text = "Patient MRN: 12345678."
    redacted, result = redact_phi(text, method=RedactionMethod.MASK)

    assert "12345678" not in redacted
    assert "[MRN]" in redacted


def test_redact_date():
    """Test date detection (MM/DD/YYYY)."""
    text = "DOB: 03/15/1985."
    redacted, result = redact_phi(text, method=RedactionMethod.MASK)

    assert "03/15/1985" not in redacted
    assert "[DATE]" in redacted


def test_redact_date_iso():
    """Test ISO date detection (YYYY-MM-DD)."""
    text = "Admitted 2024-01-15."
    redacted, result = redact_phi(text, method=RedactionMethod.MASK)

    assert "2024-01-15" not in redacted


def test_redact_url():
    """Test URL detection."""
    text = "Records at https://patient-portal.example.com/records."
    redacted, result = redact_phi(text, method=RedactionMethod.MASK)

    assert "https://patient-portal.example.com" not in redacted
    assert "[URL]" in redacted


def test_redact_hash_method():
    """Test hash redaction method produces hash prefix."""
    text = "SSN 123-45-6789."
    redacted, result = redact_phi(text, method=RedactionMethod.HASH)

    assert "123-45-6789" not in redacted
    assert "[SSN:" in redacted


def test_redact_remove_method():
    """Test remove redaction method deletes PHI."""
    text = "Email: test@example.com is on file."
    redacted, result = redact_phi(text, method=RedactionMethod.REMOVE)

    assert "test@example.com" not in redacted
    assert "[EMAIL]" not in redacted  # Removed entirely


def test_redact_no_phi():
    """Test text without PHI is unchanged."""
    text = "Patient presents with chest pain and shortness of breath."
    redacted, result = redact_phi(text, method=RedactionMethod.MASK)

    assert redacted == text
    assert result.had_phi is False


def test_redact_multiple_phi():
    """Test multiple PHI items in one text."""
    text = "Patient SSN 123-45-6789, call (555) 123-4567, email test@example.com."
    redacted, result = redact_phi(text, method=RedactionMethod.MASK)

    assert "123-45-6789" not in redacted
    assert "(555) 123-4567" not in redacted
    assert "test@example.com" not in redacted
    assert result.redaction_count >= 3


def test_redact_category_filter():
    """Test redacting only specific PHI categories."""
    text = "SSN 123-45-6789, email test@example.com."
    redacted, result = redact_phi(
        text,
        method=RedactionMethod.MASK,
        categories={PHICategory.SSN},
    )

    assert "123-45-6789" not in redacted
    assert "test@example.com" in redacted  # Email not redacted


def test_contains_phi_true():
    """Test quick PHI check returns True."""
    assert contains_phi("Patient SSN 123-45-6789") is True


def test_contains_phi_false():
    """Test quick PHI check returns False."""
    assert contains_phi("Patient presents with headache") is False


def test_redact_dict():
    """Test recursive dict PHI redaction."""
    data = {
        "name": "John Doe",
        "ssn": "123-45-6789",
        "notes": "Call 555-123-4567.",
        "nested": {
            "email": "test@example.com",
        },
        "codes": ["I10", "E11.42"],
        "count": 5,
    }
    redacted = redact_dict(data, method=RedactionMethod.MASK)

    assert "123-45-6789" not in redacted["ssn"]
    assert "test@example.com" not in redacted["nested"]["email"]
    assert redacted["codes"] == ["I10", "E11.42"]  # Non-PHI lists preserved
    assert redacted["count"] == 5


# ============================================================================
# Audit Logger Tests
# ============================================================================


def test_audit_logger_creates_entry():
    """Test audit logger creates entries."""
    with tempfile.NamedTemporaryFile(suffix=".log", delete=False) as f:
        log_path = f.name

    try:
        audit = AuditLogger(log_path=log_path)
        entry = audit.log(
            action=AuditAction.PROCESS,
            outcome=AuditOutcome.SUCCESS,
            agent_name="clinical_documentation",
            workflow_id="wf-001",
            patient_id="P12345",
            resource_type="clinical_note",
            detail="Processed clinical note",
        )

        assert entry.action == "process"
        assert entry.outcome == "success"
        assert entry.agent_name == "clinical_documentation"
        assert entry.patient_id_hash != ""
        assert entry.patient_id_hash != "P12345"  # Hashed, not raw
        assert audit.entry_count == 1
    finally:
        os.unlink(log_path)


def test_audit_logger_writes_to_file():
    """Test audit entries are written to file."""
    with tempfile.NamedTemporaryFile(suffix=".log", delete=False) as f:
        log_path = f.name

    try:
        audit = AuditLogger(log_path=log_path)
        audit.log(
            action=AuditAction.VIEW,
            outcome=AuditOutcome.SUCCESS,
            resource_type="patient_record",
        )
        audit.log(
            action=AuditAction.CODE_SUGGEST,
            outcome=AuditOutcome.SUCCESS,
            agent_name="medical_coding",
        )

        with open(log_path, encoding="utf-8") as f:
            lines = f.readlines()

        assert len(lines) == 2

        entry1 = json.loads(lines[0])
        assert entry1["action"] == "view"

        entry2 = json.loads(lines[1])
        assert entry2["action"] == "code_suggest"
    finally:
        os.unlink(log_path)


def test_audit_logger_patient_id_hashed():
    """Test patient IDs are consistently hashed."""
    with tempfile.NamedTemporaryFile(suffix=".log", delete=False) as f:
        log_path = f.name

    try:
        audit = AuditLogger(log_path=log_path)
        entry1 = audit.log(
            action=AuditAction.VIEW,
            outcome=AuditOutcome.SUCCESS,
            patient_id="P12345",
        )
        entry2 = audit.log(
            action=AuditAction.PROCESS,
            outcome=AuditOutcome.SUCCESS,
            patient_id="P12345",
        )

        # Same patient ID should produce same hash
        assert entry1.patient_id_hash == entry2.patient_id_hash
        assert len(entry1.patient_id_hash) == 16
    finally:
        os.unlink(log_path)


def test_audit_logger_query_by_action():
    """Test querying entries by action type."""
    with tempfile.NamedTemporaryFile(suffix=".log", delete=False) as f:
        log_path = f.name

    try:
        audit = AuditLogger(log_path=log_path)
        audit.log(action=AuditAction.VIEW, outcome=AuditOutcome.SUCCESS)
        audit.log(action=AuditAction.PROCESS, outcome=AuditOutcome.SUCCESS)
        audit.log(action=AuditAction.VIEW, outcome=AuditOutcome.FAILURE)

        views = audit.get_entries(action=AuditAction.VIEW)
        assert len(views) == 2

        processes = audit.get_entries(action=AuditAction.PROCESS)
        assert len(processes) == 1
    finally:
        os.unlink(log_path)


def test_audit_logger_query_by_workflow():
    """Test querying entries by workflow ID."""
    with tempfile.NamedTemporaryFile(suffix=".log", delete=False) as f:
        log_path = f.name

    try:
        audit = AuditLogger(log_path=log_path)
        audit.log(action=AuditAction.PROCESS, outcome=AuditOutcome.SUCCESS, workflow_id="wf-1")
        audit.log(action=AuditAction.PROCESS, outcome=AuditOutcome.SUCCESS, workflow_id="wf-2")
        audit.log(action=AuditAction.QA_REVIEW, outcome=AuditOutcome.SUCCESS, workflow_id="wf-1")

        wf1 = audit.get_entries(workflow_id="wf-1")
        assert len(wf1) == 2
    finally:
        os.unlink(log_path)


def test_audit_entry_to_json():
    """Test audit entry serialization."""
    with tempfile.NamedTemporaryFile(suffix=".log", delete=False) as f:
        log_path = f.name

    try:
        audit = AuditLogger(log_path=log_path)
        entry = audit.log(
            action=AuditAction.COMPLIANCE_CHECK,
            outcome=AuditOutcome.SUCCESS,
            agent_name="compliance",
        )

        json_str = entry.to_json()
        parsed = json.loads(json_str)

        assert parsed["action"] == "compliance_check"
        assert parsed["outcome"] == "success"
        assert parsed["agent_name"] == "compliance"
        assert "timestamp" in parsed
    finally:
        os.unlink(log_path)


# ============================================================================
# Encryption Tests
# ============================================================================


def test_encrypt_decrypt_roundtrip():
    """Test encryption and decryption roundtrip."""
    with tempfile.NamedTemporaryFile(suffix=".key", delete=False) as f:
        key_path = f.name

    try:
        # Remove file so EncryptionManager generates a new key
        os.unlink(key_path)

        manager = EncryptionManager(key_path=key_path)
        plaintext = "Sensitive patient data: SSN 123-45-6789"

        ciphertext = manager.encrypt(plaintext)
        assert ciphertext != plaintext

        decrypted = manager.decrypt(ciphertext)
        assert decrypted == plaintext
    finally:
        if os.path.exists(key_path):
            os.unlink(key_path)


def test_encrypt_dict_roundtrip():
    """Test dictionary encryption roundtrip."""
    with tempfile.NamedTemporaryFile(suffix=".key", delete=False) as f:
        key_path = f.name

    try:
        os.unlink(key_path)
        manager = EncryptionManager(key_path=key_path)

        data = {"patient_id": "P123", "codes": ["I10", "E11.42"], "score": 95}

        ciphertext = manager.encrypt_dict(data)
        assert isinstance(ciphertext, str)

        decrypted = manager.decrypt_dict(ciphertext)
        assert decrypted == data
    finally:
        if os.path.exists(key_path):
            os.unlink(key_path)


def test_encrypt_different_outputs():
    """Test same plaintext produces different ciphertexts (nonce/IV)."""
    with tempfile.NamedTemporaryFile(suffix=".key", delete=False) as f:
        key_path = f.name

    try:
        os.unlink(key_path)
        manager = EncryptionManager(key_path=key_path)

        plaintext = "Test data"
        ct1 = manager.encrypt(plaintext)
        ct2 = manager.encrypt(plaintext)

        # Fernet and HMAC both use randomness, so ciphertexts should differ
        assert ct1 != ct2

        # But both should decrypt correctly
        assert manager.decrypt(ct1) == plaintext
        assert manager.decrypt(ct2) == plaintext
    finally:
        if os.path.exists(key_path):
            os.unlink(key_path)


def test_encryption_key_persistence():
    """Test encryption key persists across instances."""
    with tempfile.NamedTemporaryFile(suffix=".key", delete=False) as f:
        key_path = f.name

    try:
        os.unlink(key_path)

        # First instance generates key and encrypts
        manager1 = EncryptionManager(key_path=key_path)
        ciphertext = manager1.encrypt("Secret message")

        # Second instance loads same key and decrypts
        manager2 = EncryptionManager(key_path=key_path)
        decrypted = manager2.decrypt(ciphertext)

        assert decrypted == "Secret message"
    finally:
        if os.path.exists(key_path):
            os.unlink(key_path)


def test_encryption_method_reported():
    """Test encryption method is reported."""
    with tempfile.NamedTemporaryFile(suffix=".key", delete=False) as f:
        key_path = f.name

    try:
        os.unlink(key_path)
        manager = EncryptionManager(key_path=key_path)

        # Should be either "fernet" or "hmac_obfuscate"
        assert manager.method in ("fernet", "hmac_obfuscate")
    finally:
        if os.path.exists(key_path):
            os.unlink(key_path)
