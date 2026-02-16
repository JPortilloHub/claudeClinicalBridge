-- PostgreSQL initialization script for Clinical Bridge
-- Creates tables for payer policies and audit logging

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Payer policies table
CREATE TABLE IF NOT EXISTS payer_policies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    payer VARCHAR(255) NOT NULL,
    cpt_code VARCHAR(10),
    icd10_code VARCHAR(10),
    requires_prior_auth BOOLEAN DEFAULT false,
    documentation_requirements JSONB,
    medical_necessity_criteria JSONB,
    effective_date DATE NOT NULL,
    expiration_date DATE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT check_code_present CHECK (
        cpt_code IS NOT NULL OR icd10_code IS NOT NULL
    )
);

-- Index for faster lookups
CREATE INDEX idx_payer_policies_payer ON payer_policies(payer);
CREATE INDEX idx_payer_policies_cpt ON payer_policies(cpt_code) WHERE cpt_code IS NOT NULL;
CREATE INDEX idx_payer_policies_icd10 ON payer_policies(icd10_code) WHERE icd10_code IS NOT NULL;
CREATE INDEX idx_payer_policies_effective ON payer_policies(effective_date);

-- Composite indexes for common query patterns
CREATE INDEX idx_payer_policies_payer_cpt ON payer_policies(payer, cpt_code) WHERE cpt_code IS NOT NULL;
CREATE INDEX idx_payer_policies_payer_icd10 ON payer_policies(payer, icd10_code) WHERE icd10_code IS NOT NULL;

-- Audit log table (HIPAA compliance)
CREATE TABLE IF NOT EXISTS audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    user_id VARCHAR(255),
    patient_id_hash VARCHAR(64),  -- Hashed patient ID for privacy
    resource_type VARCHAR(100),
    resource_id VARCHAR(255),
    action VARCHAR(50) NOT NULL,
    result VARCHAR(50) NOT NULL,
    ip_address INET,
    details JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Index for audit log queries
CREATE INDEX idx_audit_log_timestamp ON audit_log(timestamp DESC);
CREATE INDEX idx_audit_log_event_type ON audit_log(event_type);
CREATE INDEX idx_audit_log_patient ON audit_log(patient_id_hash);
CREATE INDEX idx_audit_log_user ON audit_log(user_id);

-- Trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_payer_policies_updated_at
    BEFORE UPDATE ON payer_policies
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Sample payer policy data
INSERT INTO payer_policies (
    payer,
    cpt_code,
    requires_prior_auth,
    documentation_requirements,
    medical_necessity_criteria,
    effective_date
) VALUES
(
    'Medicare',
    '99214',
    false,
    '["Chief complaint", "History of present illness (4+ elements)", "Review of systems (2+ systems)", "Moderate complexity MDM"]'::jsonb,
    '["Established patient", "Follow-up care", "Moderate medical decision making"]'::jsonb,
    '2024-01-01'
),
(
    'Medicare',
    '99215',
    false,
    '["Chief complaint", "Comprehensive HPI", "Complete ROS (10+ systems)", "Detailed examination", "High complexity MDM"]'::jsonb,
    '["Established patient", "Complex medical condition", "High medical decision making"]'::jsonb,
    '2024-01-01'
),
(
    'Medicare',
    '70553',
    true,
    '["Clinical indication", "Prior conservative treatment documented", "Relevant physical exam findings"]'::jsonb,
    '["Brain MRI with contrast", "Suspected tumor or infection", "Failed conservative management"]'::jsonb,
    '2024-01-01'
),
(
    'Commercial',
    '99214',
    false,
    '["Chief complaint", "HPI", "Examination", "MDM"]'::jsonb,
    '["Established patient visit", "Moderate complexity"]'::jsonb,
    '2024-01-01'
),
(
    'Commercial',
    '45378',
    true,
    '["Screening indication", "Age ≥45 or family history", "No contraindications documented"]'::jsonb,
    '["Colonoscopy screening", "Age appropriate or high risk", "No recent colonoscopy"]'::jsonb,
    '2024-01-01'
);

-- Grant privileges
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO clinical_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO clinical_user;
