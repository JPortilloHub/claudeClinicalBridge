/**
 * Zod schemas and ViewModel types for phase data validation.
 *
 * Each phase has a Zod schema that validates backend JSON,
 * plus a PhaseViewModel that the UI renders exclusively.
 */

import { z } from 'zod';

/* ------------------------------------------------------------------ */
/*  Shared types                                                       */
/* ------------------------------------------------------------------ */

export interface KPIItem {
  label: string;
  value: string | number;
  color?: 'green' | 'yellow' | 'red' | 'blue' | 'gray';
}

export interface Section {
  title: string;
  content: unknown;
}

export interface PhaseViewModel {
  status: 'completed' | 'running' | 'failed' | 'unknown';
  summary: string;
  kpis: KPIItem[];
  sections: Section[];
  raw?: unknown;
}

/* ------------------------------------------------------------------ */
/*  Clinical Documentation schema                                      */
/* ------------------------------------------------------------------ */

export const DocumentationSchema = z.object({
  subjective: z.object({
    chief_complaint: z.string().optional(),
    hpi: z.record(z.string(), z.unknown()).optional(),
    ros: z.record(z.string(), z.unknown()).optional(),
    pmh: z.array(z.string()).optional(),
    medications: z.array(z.string()).optional(),
    allergies: z.array(z.string()).optional(),
  }).optional(),
  objective: z.object({
    vitals: z.record(z.string(), z.unknown()).optional(),
    physical_exam: z.record(z.string(), z.unknown()).optional(),
    labs: z.array(z.unknown()).optional(),
    imaging: z.array(z.unknown()).optional(),
  }).optional(),
  assessment: z.array(z.object({
    diagnosis: z.string().optional(),
    icd10_hint: z.string().optional(),
    clinical_reasoning: z.string().optional(),
    pertinent_positives: z.array(z.string()).optional(),
    pertinent_negatives: z.array(z.string()).optional(),
  })).optional(),
  plan: z.array(z.object({
    diagnosis: z.string().optional(),
    actions: z.array(z.string()).optional(),
  })).optional(),
  documentation_gaps: z.array(z.union([z.string(), z.object({}).passthrough()])).optional(),
  coding_hints: z.record(z.string(), z.unknown()).optional(),
}).passthrough();

/* ------------------------------------------------------------------ */
/*  Medical Coding schema                                              */
/* ------------------------------------------------------------------ */

export const CodingSchema = z.object({
  diagnoses: z.array(z.object({
    code: z.string().optional(),
    description: z.string().optional(),
    sequencing: z.string().optional(),
    confidence: z.string().optional(),
    rationale: z.string().optional(),
    specificity_check: z.string().optional(),
    modifiers: z.array(z.string()).optional(),
    supporting_documentation: z.array(z.string()).optional(),
    excludes_conflicts: z.string().optional(),
  })).optional(),
  procedures: z.array(z.object({
    code: z.string().optional(),
    description: z.string().optional(),
    confidence: z.string().optional(),
    rationale: z.string().optional(),
    modifiers: z.array(z.string()).optional(),
  })).optional(),
  em_calculation: z.object({
    method: z.string().optional(),
    problems: z.string().optional(),
    data: z.string().optional(),
    risk: z.string().optional(),
    level: z.string().optional(),
    code: z.string().optional(),
  }).optional(),
  coding_notes: z.array(z.string()).optional(),
  queries_needed: z.array(z.string()).optional(),
}).passthrough();

/* ------------------------------------------------------------------ */
/*  Compliance Validation schema                                       */
/* ------------------------------------------------------------------ */

export const ComplianceSchema = z.object({
  overall_status: z.string().optional(),
  risk_level: z.string().optional(),
  audit_readiness_score: z.number().optional(),
  code_validations: z.array(z.object({
    code: z.string().optional(),
    status: z.string().optional(),
    documentation_support: z.string().optional(),
    issues: z.array(z.string()).optional(),
  })).optional(),
  em_validation: z.object({
    documented_level: z.string().optional(),
    supported_level: z.string().optional(),
    status: z.string().optional(),
    issues: z.array(z.string()).optional(),
  }).optional(),
  compliance_issues: z.array(z.object({
    severity: z.string().optional(),
    category: z.string().optional(),
    description: z.string().optional(),
    regulatory_reference: z.string().optional(),
    remediation: z.union([z.string(), z.array(z.string())]).optional(),
  })).optional(),
  payer_checks: z.object({
    prior_auth_required: z.boolean().optional(),
    documentation_complete: z.boolean().optional(),
    missing_elements: z.array(z.string()).optional(),
  }).optional(),
}).passthrough();

/* ------------------------------------------------------------------ */
/*  Prior Authorization schema                                         */
/* ------------------------------------------------------------------ */

export const PriorAuthSchema = z.object({
  procedure: z.object({
    cpt_code: z.string().optional(),
    description: z.string().optional(),
    payer: z.string().optional(),
  }).optional(),
  prior_auth_required: z.boolean().optional(),
  approval_likelihood: z.string().optional(),
  approval_likelihood_rationale: z.string().optional(),
  criteria_assessment: z.object({
    criteria_met: z.array(z.object({
      criterion: z.string().optional(),
      supporting_evidence: z.string().optional(),
      status: z.string().optional(),
    })).optional(),
    criteria_not_met: z.array(z.object({
      criterion: z.string().optional(),
      status: z.string().optional(),
      supporting_evidence: z.string().optional(),
      action_needed: z.string().optional(),
    })).optional(),
  }).optional(),
  documentation_checklist: z.object({
    complete: z.array(z.string()).optional(),
    partial: z.array(z.string()).optional(),
    missing: z.array(z.string()).optional(),
  }).optional(),
  medical_necessity_summary: z.string().optional(),
  recommended_actions: z.array(z.string()).optional(),
  appeal_considerations: z.array(z.string()).optional(),
}).passthrough();

/* ------------------------------------------------------------------ */
/*  Quality Assurance schema                                           */
/* ------------------------------------------------------------------ */

export const QualitySchema = z.object({
  overall_quality: z.string().optional(),
  quality_score: z.number().optional(),
  ready_for_submission: z.boolean().optional(),
  dimensions: z.record(z.string(), z.object({
    score: z.number().optional(),
  }).passthrough()).optional(),
  critical_issues: z.array(z.string()).optional(),
  warnings: z.array(z.object({
    category: z.string().optional(),
    description: z.string().optional(),
    recommendation: z.string().optional(),
  }).passthrough()).optional(),
  improvements: z.array(z.string()).optional(),
  traceability: z.object({
    all_codes_traceable: z.boolean().optional(),
    untraceable_items: z.array(z.string()).optional(),
  }).optional(),
}).passthrough();

/* ------------------------------------------------------------------ */
/*  Validated types (inferred from schemas)                            */
/* ------------------------------------------------------------------ */

export type DocumentationData = z.infer<typeof DocumentationSchema>;
export type CodingData = z.infer<typeof CodingSchema>;
export type ComplianceData = z.infer<typeof ComplianceSchema>;
export type PriorAuthData = z.infer<typeof PriorAuthSchema>;
export type QualityData = z.infer<typeof QualitySchema>;
