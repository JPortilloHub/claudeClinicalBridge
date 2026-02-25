/**
 * Phase parser functions that transform raw backend JSON into PhaseViewModels.
 *
 * Each parser validates with Zod, extracts KPIs and summary,
 * and returns a structured ViewModel. On failure, returns a fallback.
 *
 * Handles truncated/cut-off JSON from LLM token limits via jsonRepair.
 */

import type { PhaseViewModel, KPIItem } from '../types/schemas';
import {
  DocumentationSchema,
  CodingSchema,
  ComplianceSchema,
  PriorAuthSchema,
  QualitySchema,
} from '../types/schemas';
import { parseJsonSafe } from './jsonRepair';

/* ------------------------------------------------------------------ */
/*  JSON extraction                                                    */
/* ------------------------------------------------------------------ */

function extractJson(raw: string): string {
  const s = raw.trim();
  if (s.startsWith('{') || s.startsWith('[')) return s;

  // Try fenced code blocks — greedy capture to get full block content
  const fenceMatch = s.match(/```(?:json)?\s*\n?([\s\S]+?)\n?\s*```/);
  if (fenceMatch) return fenceMatch[1].trim();

  const firstBrace = s.indexOf('{');
  const lastBrace = s.lastIndexOf('}');
  if (firstBrace !== -1 && lastBrace > firstBrace) {
    return s.slice(firstBrace, lastBrace + 1);
  }

  // For truncated JSON, there may be no closing brace — grab from first {
  if (firstBrace !== -1) {
    return s.slice(firstBrace);
  }

  return s;
}

/* ------------------------------------------------------------------ */
/*  Markdown-embedded JSON helpers                                     */
/* ------------------------------------------------------------------ */

interface JsonBlockWithContext {
  json: unknown;
  precedingText: string;
}

/**
 * Extract ALL fenced JSON code blocks from a markdown string,
 * each with the preceding ~200 chars for context-based classification.
 */
function extractAllJsonBlocks(raw: string): JsonBlockWithContext[] {
  if (typeof raw !== 'string') return [];
  const results: JsonBlockWithContext[] = [];
  const fenceRe = /```(?:json)?\s*\n?([\s\S]+?)\n?\s*```/g;
  let match;
  while ((match = fenceRe.exec(raw)) !== null) {
    const preceding = raw.slice(Math.max(0, match.index - 300), match.index);
    try {
      const parsed = JSON.parse(match[1].trim());
      results.push({ json: parsed, precedingText: preceding });
    } catch {
      const repaired = parseJsonSafe(match[1].trim());
      if (repaired !== null) {
        results.push({ json: repaired, precedingText: preceding });
      }
    }
  }
  return results;
}

/**
 * Extract a value from markdown prose using a regex pattern.
 * Strips markdown bold/italic markers (** and *) from the input before matching,
 * so regex patterns can match plain text without worrying about formatting.
 * Returns the first capture group or null.
 */
function extractMarkdownField(raw: string, pattern: RegExp): string | null {
  if (typeof raw !== 'string') return null;
  // Strip markdown bold/italic markers so regexes match plain text
  const stripped = raw.replace(/\*+/g, '');
  const m = stripped.match(pattern);
  return m ? m[1].trim() : null;
}

/**
 * Parse JSON with repair support for truncated LLM outputs.
 * Returns [parsed, wasTruncated] — wasTruncated is true if repair was needed.
 * Accepts a string or an already-parsed object (from some API code paths).
 */
function safeParse(raw: string | object): [unknown, boolean] {
  // If content is already a parsed object, return it directly
  if (typeof raw === 'object' && raw !== null) {
    return [raw, false];
  }

  if (typeof raw !== 'string' || raw.trim().length === 0) {
    return [null, false];
  }

  // Strategy 1: Extract JSON substring and parse directly
  const extracted = extractJson(raw);
  try {
    return [JSON.parse(extracted), false];
  } catch {
    // continue
  }

  // Strategy 2: Try parsing the raw string directly (in case extractJson mangled it)
  try {
    return [JSON.parse(raw.trim()), false];
  } catch {
    // continue
  }

  // Strategy 3: Repair the extracted JSON
  const repaired = parseJsonSafe(extracted);
  if (repaired !== null) {
    return [repaired, true];
  }

  // Strategy 4: Repair the raw string (in case extraction was the issue)
  if (extracted !== raw.trim()) {
    const repairedRaw = parseJsonSafe(raw.trim());
    if (repairedRaw !== null) {
      return [repairedRaw, true];
    }
  }

  console.warn('[phaseParsers] All parse strategies failed. First 500 chars:', raw.slice(0, 500));
  return [null, true];
}

/* ------------------------------------------------------------------ */
/*  Fallback builder                                                   */
/* ------------------------------------------------------------------ */

function buildFallback(raw: string | object, error?: string): PhaseViewModel {
  const rawStr = typeof raw === 'string' ? raw : JSON.stringify(raw, null, 2);

  // Even when JSON parsing fails, show the content in a readable way.
  // Try to split on markdown headers to create structured sections.
  const sections: { title: string; content: unknown }[] = [];

  if (rawStr.length > 0) {
    const headerPattern = /(?:^|\n)#{1,4}\s+(.+)/g;
    let match;
    const breaks: { title: string; contentStart: number; headerStart: number }[] = [];
    while ((match = headerPattern.exec(rawStr)) !== null) {
      breaks.push({
        title: match[1].trim(),
        contentStart: match.index + match[0].length,
        headerStart: match.index,
      });
    }

    if (breaks.length >= 2) {
      for (let i = 0; i < breaks.length; i++) {
        const end = i + 1 < breaks.length ? breaks[i + 1].headerStart : rawStr.length;
        const chunk = rawStr.slice(breaks[i].contentStart, end).trim();
        if (chunk) {
          sections.push({ title: breaks[i].title, content: chunk });
        }
      }
    } else {
      sections.push({ title: 'Agent Output', content: rawStr });
    }
  }

  return {
    status: 'unknown',
    summary: error || 'Displaying as text',
    kpis: [{ label: 'Format', value: 'Text', color: 'yellow' as const }],
    sections: sections.length > 0 ? sections : [{ title: 'Agent Output', content: rawStr }],
    raw,
  };
}

/** Add a "partial data" KPI indicator when JSON was truncated */
function addTruncationWarning(kpis: KPIItem[], wasTruncated: boolean): void {
  if (wasTruncated) {
    kpis.push({ label: 'Data', value: 'Partial', color: 'yellow' });
  }
}

/* ------------------------------------------------------------------ */
/*  Clinical Documentation parser                                      */
/* ------------------------------------------------------------------ */

export function parseClinicalDocumentation(raw: string | object): PhaseViewModel {
  const [json, wasTruncated] = safeParse(raw);
  if (json === null || typeof json !== 'object') {
    return buildFallback(raw, 'Unable to parse documentation output');
  }

  try {
    const result = DocumentationSchema.safeParse(json);
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    let data = (result.success ? result.data : json) as any;

    const kpis: KPIItem[] = [];
    const subjective = data?.subjective;
    const chiefComplaint = subjective?.chief_complaint as string | undefined;
    if (chiefComplaint) {
      kpis.push({ label: 'Chief Complaint', value: chiefComplaint });
    }

    const assessment = data?.assessment;
    if (Array.isArray(assessment)) {
      kpis.push({ label: 'Diagnoses', value: assessment.length, color: 'blue' });
    }

    const gaps = data?.documentation_gaps;
    if (Array.isArray(gaps) && gaps.length > 0) {
      kpis.push({ label: 'Doc Gaps', value: gaps.length, color: 'yellow' });
    } else {
      kpis.push({ label: 'Doc Gaps', value: 0, color: 'green' });
    }

    const plan = data?.plan;
    if (Array.isArray(plan)) {
      kpis.push({ label: 'Plan Items', value: plan.length, color: 'blue' });
    }

    addTruncationWarning(kpis, wasTruncated);

    // Extract "Summary of Key Findings" from markdown prose after the JSON block
    if (typeof raw === 'string' && !data.key_findings) {
      const keyFindings: Record<string, unknown> = {};
      const clinicalProblemMatch = raw.match(/###\s*Clinical Problem Representation\s*\n+\*\*([\s\S]*?)\*\*/);
      if (clinicalProblemMatch) {
        keyFindings.clinical_problem = clinicalProblemMatch[1].trim();
      }
      const criticalGapsMatch = raw.match(/###\s*Most Critical Documentation Gaps\s*\n+([\s\S]*?)(?=\n###|\n##|$)/);
      if (criticalGapsMatch) {
        const lines = criticalGapsMatch[1].split('\n')
          .filter(l => /^\d+\.\s+/.test(l.trim()))
          .map(l => l.replace(/^\d+\.\s+/, '').replace(/\*\*/g, '').trim());
        if (lines.length > 0) keyFindings.critical_gaps = lines;
      }
      const codingRecsMatch = raw.match(/###\s*Coding Optimization Recommendations\s*\n+([\s\S]*?)(?=\n###|\n##|$)/);
      if (codingRecsMatch) {
        const lines = codingRecsMatch[1].split('\n')
          .filter(l => /^[-*]\s+/.test(l.trim()))
          .map(l => l.replace(/^[-*]\s+/, '').replace(/\*\*/g, '').trim());
        if (lines.length > 0) keyFindings.coding_recommendations = lines;
      }
      if (Object.keys(keyFindings).length > 0) {
        data = { ...data, key_findings: keyFindings };
      }
    }

    const summary = chiefComplaint
      ? `SOAP note for: ${chiefComplaint}`
      : 'Clinical documentation structured as SOAP note';

    return {
      status: 'completed',
      summary: wasTruncated ? summary + ' (partial output)' : summary,
      kpis,
      sections: [
        { title: 'Subjective', content: data?.subjective },
        { title: 'Objective', content: data?.objective },
        { title: 'Assessment', content: data?.assessment },
        { title: 'Plan', content: data?.plan },
        { title: 'Documentation Gaps', content: data?.documentation_gaps },
        { title: 'Coding Hints', content: data?.coding_hints },
      ].filter(s => s.content != null),
      raw: data,
    };
  } catch (e) {
    return buildFallback(raw, e instanceof Error ? e.message : 'Parse error');
  }
}

/* ------------------------------------------------------------------ */
/*  Medical Coding parser                                              */
/* ------------------------------------------------------------------ */

export function parseMedicalCoding(raw: string | object): PhaseViewModel {
  const [json, wasTruncated] = safeParse(raw);
  if (json === null || typeof json !== 'object') {
    // Even with no top-level JSON, try assembling from markdown blocks
    if (typeof raw === 'string') {
      const assembled = assembleCodingFromMarkdown(raw);
      if (assembled) {
        return parseMedicalCoding(assembled);
      }
    }
    return buildFallback(raw, 'Unable to parse coding output');
  }

  try {
    const result = CodingSchema.safeParse(json);
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    let data = (result.success ? result.data : json) as any;

    // If the parsed JSON is a single code object (has 'code' but no 'diagnoses'),
    // or has empty arrays, try assembling from markdown blocks
    const hasDiagnoses = Array.isArray(data?.diagnoses) && data.diagnoses.length > 0;
    const hasProcedures = Array.isArray(data?.procedures) && data.procedures.length > 0;
    if (!hasDiagnoses && !hasProcedures && typeof raw === 'string') {
      const assembled = assembleCodingFromMarkdown(raw);
      if (assembled) {
        data = assembled;
      }
    }

    const kpis: KPIItem[] = [];
    const diagnoses = data?.diagnoses || [];
    const procedures = data?.procedures || [];

    kpis.push({ label: 'ICD-10 Codes', value: diagnoses.length, color: 'blue' });
    kpis.push({ label: 'CPT Codes', value: procedures.length, color: 'blue' });

    if (data?.em_calculation?.level) {
      kpis.push({ label: 'E/M Level', value: data.em_calculation.level, color: 'green' });
    }

    const queries = data?.queries_needed || [];
    if (queries.length > 0) {
      kpis.push({ label: 'Queries', value: queries.length, color: 'yellow' });
    }

    addTruncationWarning(kpis, wasTruncated);

    const primary = diagnoses.find((d: { sequencing?: string }) => d.sequencing?.toLowerCase() === 'primary');
    const summary = primary?.description
      ? `Primary: ${primary.description} (${primary.code || ''})`
      : `${diagnoses.length} diagnoses, ${procedures.length} procedures coded`;

    return {
      status: 'completed',
      summary: wasTruncated ? summary + ' (partial output)' : summary,
      kpis,
      sections: [
        { title: 'Diagnoses', content: data?.diagnoses },
        { title: 'Procedures', content: data?.procedures },
        { title: 'E/M Calculation', content: data?.em_calculation },
        { title: 'Coding Notes', content: data?.coding_notes },
        { title: 'Queries Needed', content: data?.queries_needed },
      ].filter(s => s.content != null),
      raw: data,
    };
  } catch (e) {
    return buildFallback(raw, e instanceof Error ? e.message : 'Parse error');
  }
}

/**
 * Assemble a coding data object from markdown with multiple embedded JSON blocks.
 * Classifies blocks by surrounding header context (ICD-10/diagnosis vs CPT/procedure vs E/M).
 */
function assembleCodingFromMarkdown(raw: string): Record<string, unknown> | null {
  const blocks = extractAllJsonBlocks(raw);
  if (blocks.length === 0) return null;

  const diagnoses: unknown[] = [];
  const procedures: unknown[] = [];
  let emCalculation: unknown = null;
  const codingNotes: string[] = [];
  const queriesNeeded: string[] = [];

  for (const block of blocks) {
    const ctx = block.precedingText.toLowerCase();
    const obj = block.json as Record<string, unknown>;

    // If a block already has the full structure, return it directly
    if (obj && (Array.isArray(obj.diagnoses) || Array.isArray(obj.procedures))) {
      return obj;
    }

    // Classify by preceding markdown context
    const isDiagnosis = /icd[- ]?10|diagnos/i.test(ctx);
    const isProcedure = /cpt|procedure/i.test(ctx);
    const isEM = /e\/?m\s|evaluation.*management/i.test(ctx);

    if (isEM || (obj?.method && obj?.level)) {
      emCalculation = obj;
    } else if (isProcedure || (!isDiagnosis && obj?.code && /^\d{5}/.test(String(obj.code)))) {
      // CPT codes are 5-digit
      if (Array.isArray(obj)) { procedures.push(...obj); } else { procedures.push(obj); }
    } else if (isDiagnosis || (obj?.code && /^[A-Z]\d/.test(String(obj.code)))) {
      // ICD-10 codes start with a letter followed by digit
      if (Array.isArray(obj)) { diagnoses.push(...obj); } else { diagnoses.push(obj); }
    } else if (obj?.code) {
      // Fallback: classify by code format
      const code = String(obj.code);
      if (/^[A-Z]\d/.test(code)) { diagnoses.push(obj); }
      else if (/^\d{5}/.test(code)) { procedures.push(obj); }
      else { diagnoses.push(obj); }
    }
  }

  // Extract coding notes and queries from markdown if present
  const notesMatch = raw.match(/coding.?notes[:\s]*\n([\s\S]*?)(?=\n#|$)/i);
  if (notesMatch) {
    notesMatch[1].split('\n').filter(l => l.trim().startsWith('-') || l.trim().startsWith('*'))
      .forEach(l => codingNotes.push(l.replace(/^[\s\-*]+/, '').trim()));
  }
  const queriesMatch = raw.match(/queries.?needed[:\s]*\n([\s\S]*?)(?=\n#|$)/i);
  if (queriesMatch) {
    queriesMatch[1].split('\n').filter(l => l.trim().startsWith('-') || l.trim().startsWith('*'))
      .forEach(l => queriesNeeded.push(l.replace(/^[\s\-*]+/, '').trim()));
  }

  if (diagnoses.length === 0 && procedures.length === 0 && !emCalculation) return null;

  const result: Record<string, unknown> = {};
  if (diagnoses.length > 0) result.diagnoses = diagnoses;
  if (procedures.length > 0) result.procedures = procedures;
  if (emCalculation) result.em_calculation = emCalculation;
  if (codingNotes.length > 0) result.coding_notes = codingNotes;
  if (queriesNeeded.length > 0) result.queries_needed = queriesNeeded;
  return result;
}

/* ------------------------------------------------------------------ */
/*  Compliance Validation parser                                       */
/* ------------------------------------------------------------------ */

export function parseCompliance(raw: string | object): PhaseViewModel {
  const [json, wasTruncated] = safeParse(raw);
  if (json === null || typeof json !== 'object') {
    // Try assembling from markdown
    if (typeof raw === 'string') {
      const assembled = assembleComplianceFromMarkdown(raw);
      if (assembled) {
        return parseCompliance(assembled);
      }
    }
    return buildFallback(raw, 'Unable to parse compliance output');
  }

  try {
    const result = ComplianceSchema.safeParse(json);
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    let data = (result.success ? result.data : json) as any;

    // Markdown fallback: if key fields are missing, extract from raw string
    if (typeof raw === 'string' && (!data?.overall_status || !data?.risk_level)) {
      const mdStatus = extractMarkdownField(raw, /(?:overall\s*)?compliance\s*status[:\s]*(?:⚠️\s*|✅\s*|❌\s*)?(\w[\w ]*\w)/i);
      const mdRisk = extractMarkdownField(raw, /risk\s*level[:\s]*(?:🟡\s*|🟢\s*|🔴\s*)?(\w+)/i);
      const mdScoreStr = extractMarkdownField(raw, /audit\s*(?:readiness\s*)?score[:\s]*(\d+)\s*\/\s*100/i);

      if (!data.overall_status && mdStatus) {
        data = { ...data, overall_status: mdStatus.toLowerCase().replace(/\s+/g, '_') };
      }
      if (!data.risk_level && mdRisk) {
        data = { ...data, risk_level: mdRisk.toLowerCase() };
      }
      if (data.audit_readiness_score == null && mdScoreStr) {
        data = { ...data, audit_readiness_score: parseInt(mdScoreStr, 10) };
      }

      // Collect structured data from JSON blocks using context-aware classification
      if (!data.compliance_issues || data.compliance_issues.length === 0 || !data.code_validations || !data.em_validation || !data.payer_checks) {
        const blocks = extractAllJsonBlocks(raw);
        const issues: unknown[] = [];
        const codeVals: unknown[] = [];
        let emVal: unknown = null;
        let payerChk: unknown = null;

        for (const block of blocks) {
          const classification = classifyComplianceBlock(block);
          const obj = block.json;

          if (classification === 'code_validation' && !data.code_validations) {
            if (Array.isArray(obj)) { codeVals.push(...obj); } else { codeVals.push(obj); }
          } else if (classification === 'em_validation' && !data.em_validation) {
            emVal = obj;
          } else if (classification === 'payer_checks' && !data.payer_checks) {
            payerChk = obj;
          } else if (classification === 'compliance_issue' && (!data.compliance_issues || data.compliance_issues.length === 0)) {
            if (Array.isArray(obj)) {
              issues.push(...obj.filter((item: any) => item?.severity || item?.category));
            } else if (obj && typeof obj === 'object' && ((obj as any).severity || (obj as any).risk_id)) {
              issues.push(obj);
            }
          }
        }

        if (issues.length > 0 && (!data.compliance_issues || data.compliance_issues.length === 0)) {
          data = { ...data, compliance_issues: issues };
        }
        if (codeVals.length > 0 && !data.code_validations) {
          data = { ...data, code_validations: codeVals };
        }
        if (emVal && !data.em_validation) {
          data = { ...data, em_validation: emVal };
        }
        if (payerChk && !data.payer_checks) {
          data = { ...data, payer_checks: payerChk };
        }
      }
    }

    const kpis: KPIItem[] = [];
    const status = data?.overall_status;
    const statusLower = (status || '').toLowerCase();
    const statusColor = statusLower === 'pass' ? 'green' as const
      : (statusLower === 'needs_review' || statusLower === 'needs review') ? 'yellow' as const
      : statusLower === 'fail' ? 'red' as const : 'gray' as const;

    kpis.push({ label: 'Status', value: (status || 'Unknown').replace(/_/g, ' '), color: statusColor });

    if (data?.audit_readiness_score != null) {
      const score = data.audit_readiness_score;
      kpis.push({
        label: 'Audit Score',
        value: `${score}/100`,
        color: score >= 90 ? 'green' : score >= 70 ? 'yellow' : 'red',
      });
    }

    const issues = data?.compliance_issues || [];
    const criticalCount = issues.filter((i: { severity?: string }) => i.severity?.toLowerCase() === 'critical').length;
    kpis.push({
      label: 'Issues',
      value: issues.length,
      color: criticalCount > 0 ? 'red' : issues.length > 0 ? 'yellow' : 'green',
    });

    const riskLevel = data?.risk_level;
    if (riskLevel) {
      const riskLower = riskLevel.toLowerCase();
      const riskColor = riskLower === 'low' ? 'green' as const
        : riskLower === 'medium' ? 'yellow' as const
        : riskLower === 'high' ? 'red' as const : statusColor;
      kpis.push({ label: 'Risk', value: riskLevel, color: riskColor });
    }

    addTruncationWarning(kpis, wasTruncated);

    const summary = `${(status || 'Unknown').replace(/_/g, ' ')} - ${issues.length} issue(s) found`;

    return {
      status: 'completed',
      summary: wasTruncated ? summary + ' (partial output)' : summary,
      kpis,
      sections: [
        { title: 'Code Validations', content: data?.code_validations },
        { title: 'E/M Validation', content: data?.em_validation },
        { title: 'Compliance Issues', content: data?.compliance_issues },
        { title: 'Payer Checks', content: data?.payer_checks },
      ].filter(s => s.content != null),
      raw: data,
    };
  } catch (e) {
    return buildFallback(raw, e instanceof Error ? e.message : 'Parse error');
  }
}

/**
 * Classify a JSON block from compliance markdown into its category based on
 * the block's structure and the preceding markdown text.
 */
function classifyComplianceBlock(block: JsonBlockWithContext): 'code_validation' | 'em_validation' | 'payer_checks' | 'compliance_issue' | 'unknown' {
  const ctx = block.precedingText.toLowerCase();
  const obj = block.json as Record<string, unknown>;

  // Check preceding text for context clues
  const isCodeValidation = /code\s*validation|code[- ]to[- ]documentation/i.test(ctx);
  const isEmValidation = /e\/?m\s*validation|e\/?m\s*level\s*v/i.test(ctx);
  const isPayerCheck = /payer\s*check|payer\s*requirement|payer\s*specific/i.test(ctx);
  const isComplianceRisk = /compliance\s*risk|risks?\s*identified|audit\s*risk|compliance\s*issue/i.test(ctx);

  if (isCodeValidation) return 'code_validation';
  if (isEmValidation) return 'em_validation';
  if (isPayerCheck) return 'payer_checks';
  if (isComplianceRisk) return 'compliance_issue';

  // Fallback: classify by object structure
  if (obj && typeof obj === 'object') {
    if ('documented_level' in obj || 'supported_level' in obj) return 'em_validation';
    if ('prior_auth_required' in obj || 'documentation_complete' in obj) return 'payer_checks';
    if ('code' in obj && 'status' in obj && 'documentation_support' in obj) return 'code_validation';
    if ('severity' in obj || 'risk_id' in obj) return 'compliance_issue';
  }

  return 'unknown';
}

/**
 * Assemble compliance data from a markdown response with embedded JSON blocks
 * and an executive summary in prose.
 */
function assembleComplianceFromMarkdown(raw: string): Record<string, unknown> | null {
  const mdStatus = extractMarkdownField(raw, /(?:overall\s*)?compliance\s*status[:\s]*(?:⚠️\s*|✅\s*|❌\s*)?(\w[\w ]*\w)/i);
  const mdRisk = extractMarkdownField(raw, /risk\s*level[:\s]*(?:🟡\s*|🟢\s*|🔴\s*)?(\w+)/i);
  const mdScoreStr = extractMarkdownField(raw, /audit\s*(?:readiness\s*)?score[:\s]*(\d+)\s*\/\s*100/i);

  const blocks = extractAllJsonBlocks(raw);
  const issues: unknown[] = [];
  const codeValidations: unknown[] = [];
  let emValidation: unknown = null;
  let payerChecks: unknown = null;

  for (const block of blocks) {
    const classification = classifyComplianceBlock(block);
    const obj = block.json;

    if (classification === 'code_validation') {
      if (Array.isArray(obj)) {
        codeValidations.push(...obj);
      } else {
        codeValidations.push(obj);
      }
    } else if (classification === 'em_validation') {
      emValidation = obj;
    } else if (classification === 'payer_checks') {
      payerChecks = obj;
    } else if (classification === 'compliance_issue') {
      if (Array.isArray(obj)) {
        issues.push(...obj.filter((item: any) => item?.severity || item?.category));
      } else if (obj && typeof obj === 'object' && ((obj as any).severity || (obj as any).risk_id)) {
        issues.push(obj);
      }
    }
    // 'unknown' blocks with severity but NOT in a risk section are skipped
  }

  if (!mdStatus && !mdRisk && issues.length === 0 && codeValidations.length === 0 && !emValidation && !payerChecks) return null;

  const result: Record<string, unknown> = {};
  if (mdStatus) result.overall_status = mdStatus.toLowerCase().replace(/\s+/g, '_');
  if (mdRisk) result.risk_level = mdRisk.toLowerCase();
  if (mdScoreStr) result.audit_readiness_score = parseInt(mdScoreStr, 10);
  if (issues.length > 0) result.compliance_issues = issues;
  if (codeValidations.length > 0) result.code_validations = codeValidations;
  if (emValidation) result.em_validation = emValidation;
  if (payerChecks) result.payer_checks = payerChecks;
  return result;
}

/* ------------------------------------------------------------------ */
/*  Prior Authorization parser                                         */
/* ------------------------------------------------------------------ */

export function parsePriorAuth(raw: string | object): PhaseViewModel {
  const [json, wasTruncated] = safeParse(raw);
  if (json === null || typeof json !== 'object') {
    return buildFallback(raw, 'Unable to parse prior auth output');
  }

  try {
    const result = PriorAuthSchema.safeParse(json);
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const data = (result.success ? result.data : json) as any;

    const kpis: KPIItem[] = [];

    if (data?.prior_auth_required != null) {
      kpis.push({
        label: 'Auth Required',
        value: data.prior_auth_required ? 'Yes' : 'No',
        color: data.prior_auth_required ? 'yellow' : 'green',
      });
    }

    if (data?.approval_likelihood) {
      const lk = data.approval_likelihood.toLowerCase();
      kpis.push({
        label: 'Approval',
        value: data.approval_likelihood,
        color: lk === 'high' ? 'green' : lk === 'moderate' ? 'yellow' : 'red',
      });
    }

    const met = data?.criteria_assessment?.criteria_met || [];
    const notMet = data?.criteria_assessment?.criteria_not_met || [];
    kpis.push({ label: 'Criteria Met', value: `${met.length}/${met.length + notMet.length}`, color: notMet.length === 0 ? 'green' : 'yellow' });

    addTruncationWarning(kpis, wasTruncated);

    const proc = data?.procedure;
    const summary = proc?.description
      ? `${proc.description}${proc.cpt_code ? ` (${proc.cpt_code})` : ''}`
      : 'Prior authorization assessment';

    return {
      status: 'completed',
      summary: wasTruncated ? summary + ' (partial output)' : summary,
      kpis,
      sections: [
        { title: 'Procedure', content: data?.procedure },
        { title: 'Criteria Assessment', content: data?.criteria_assessment },
        { title: 'Documentation Checklist', content: data?.documentation_checklist },
        { title: 'Medical Necessity', content: data?.medical_necessity_summary },
        { title: 'Recommended Actions', content: data?.recommended_actions },
        { title: 'Appeal Considerations', content: data?.appeal_considerations },
      ].filter(s => s.content != null),
      raw: json,
    };
  } catch (e) {
    return buildFallback(raw, e instanceof Error ? e.message : 'Parse error');
  }
}

/* ------------------------------------------------------------------ */
/*  Quality Assurance parser                                           */
/* ------------------------------------------------------------------ */

export function parseQualityAssurance(raw: string | object): PhaseViewModel {
  const [json, wasTruncated] = safeParse(raw);
  if (json === null || typeof json !== 'object') {
    // Try assembling from markdown
    if (typeof raw === 'string') {
      const assembled = assembleQualityFromMarkdown(raw);
      if (assembled) {
        return parseQualityAssurance(assembled);
      }
    }
    return buildFallback(raw, 'Unable to parse quality assurance output');
  }

  try {
    const result = QualitySchema.safeParse(json);
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    let data = (result.success ? result.data : json) as any;

    // Markdown fallback: if key fields are missing, extract from raw string
    if (typeof raw === 'string' && (!data?.overall_quality || data?.quality_score == null)) {
      const mdQuality = extractMarkdownField(raw, /overall\s*quality\s*(?:assessment)?[:\s]*(?:⚠️\s*|✅\s*|❌\s*)?(\w[\w ]*\w)/i);
      const mdScoreStr = extractMarkdownField(raw, /quality\s*score[:\s]*(\d+)\s*\/\s*100/i);
      const mdReady = extractMarkdownField(raw, /ready\s*for\s*submission[:\s]*(?:❌\s*|✅\s*)?(\w+)/i);

      if (!data.overall_quality && mdQuality) {
        data = { ...data, overall_quality: mdQuality.toLowerCase().replace(/\s+/g, '_') };
      }
      if (data.quality_score == null && mdScoreStr) {
        data = { ...data, quality_score: parseInt(mdScoreStr, 10) };
      }
      if (data.ready_for_submission == null && mdReady) {
        data = { ...data, ready_for_submission: mdReady.toLowerCase() === 'yes' };
      }

      // Collect structured data from JSON blocks
      if (!data.dimensions || !data.critical_issues) {
        const blocks = extractAllJsonBlocks(raw);
        for (const block of blocks) {
          const obj = block.json as Record<string, unknown>;
          if (obj && typeof obj === 'object') {
            if (obj.dimensions && !data.dimensions) data = { ...data, dimensions: obj.dimensions };
            if (Array.isArray(obj.critical_issues) && !data.critical_issues) data = { ...data, critical_issues: obj.critical_issues };
            if (Array.isArray(obj.warnings) && !data.warnings) data = { ...data, warnings: obj.warnings };
            if (Array.isArray(obj.improvements) && !data.improvements) data = { ...data, improvements: obj.improvements };
            if (obj.traceability && !data.traceability) data = { ...data, traceability: obj.traceability };
          }
        }
      }
    }

    const kpis: KPIItem[] = [];

    if (data?.overall_quality) {
      const q = data.overall_quality.toLowerCase();
      kpis.push({
        label: 'Quality',
        value: data.overall_quality.replace(/_/g, ' '),
        color: q === 'approved' ? 'green' : (q === 'needs_revision' || q === 'needs revision') ? 'yellow' : 'red',
      });
    }

    if (data?.quality_score != null) {
      const s = data.quality_score;
      kpis.push({
        label: 'Score',
        value: `${s}/100`,
        color: s >= 90 ? 'green' : s >= 70 ? 'yellow' : 'red',
      });
    }

    if (data?.ready_for_submission != null) {
      kpis.push({
        label: 'Ready',
        value: data.ready_for_submission ? 'Yes' : 'No',
        color: data.ready_for_submission ? 'green' : 'red',
      });
    }

    const critical = data?.critical_issues || [];
    if (critical.length > 0) {
      kpis.push({ label: 'Critical', value: critical.length, color: 'red' });
    }

    addTruncationWarning(kpis, wasTruncated);

    const summary = data?.quality_score != null
      ? `Quality score: ${data.quality_score}/100 - ${data?.ready_for_submission ? 'Ready' : 'Not ready'} for submission`
      : 'Quality assurance review';

    return {
      status: 'completed',
      summary: wasTruncated ? summary + ' (partial output)' : summary,
      kpis,
      sections: [
        { title: 'Dimensions', content: data?.dimensions },
        { title: 'Critical Issues', content: data?.critical_issues },
        { title: 'Warnings', content: data?.warnings },
        { title: 'Improvements', content: data?.improvements },
        { title: 'Traceability', content: data?.traceability },
      ].filter(s => s.content != null),
      raw: data,
    };
  } catch (e) {
    return buildFallback(raw, e instanceof Error ? e.message : 'Parse error');
  }
}

/**
 * Assemble quality data from a markdown response with embedded JSON blocks
 * and an executive summary in prose.
 */
function assembleQualityFromMarkdown(raw: string): Record<string, unknown> | null {
  const mdQuality = extractMarkdownField(raw, /overall\s*quality\s*(?:assessment)?[:\s]*(?:⚠️\s*|✅\s*|❌\s*)?(\w[\w ]*\w)/i);
  const mdScoreStr = extractMarkdownField(raw, /quality\s*score[:\s]*(\d+)\s*\/\s*100/i);
  const mdReady = extractMarkdownField(raw, /ready\s*for\s*submission[:\s]*(?:❌\s*|✅\s*)?(\w+)/i);

  const blocks = extractAllJsonBlocks(raw);

  if (!mdQuality && !mdScoreStr && blocks.length === 0) return null;

  const result: Record<string, unknown> = {};
  if (mdQuality) result.overall_quality = mdQuality.toLowerCase().replace(/\s+/g, '_');
  if (mdScoreStr) result.quality_score = parseInt(mdScoreStr, 10);
  if (mdReady) result.ready_for_submission = mdReady.toLowerCase() === 'yes';

  for (const block of blocks) {
    const obj = block.json as Record<string, unknown>;
    if (obj && typeof obj === 'object') {
      if (obj.dimensions && !result.dimensions) result.dimensions = obj.dimensions;
      if (Array.isArray(obj.critical_issues) && !result.critical_issues) result.critical_issues = obj.critical_issues;
      if (Array.isArray(obj.warnings) && !result.warnings) result.warnings = obj.warnings;
      if (Array.isArray(obj.improvements) && !result.improvements) result.improvements = obj.improvements;
      if (obj.traceability && !result.traceability) result.traceability = obj.traceability;
    }
  }

  return Object.keys(result).length > 0 ? result : null;
}

/* ------------------------------------------------------------------ */
/*  Master dispatcher                                                  */
/* ------------------------------------------------------------------ */

export function parsePhaseContent(phaseName: string, raw: string | object): PhaseViewModel {
  switch (phaseName) {
    case 'documentation':
      return parseClinicalDocumentation(raw);
    case 'coding':
      return parseMedicalCoding(raw);
    case 'compliance':
      return parseCompliance(raw);
    case 'prior_auth':
      return parsePriorAuth(raw);
    case 'quality_assurance':
      return parseQualityAssurance(raw);
    default:
      return buildFallback(raw, `Unknown phase: ${phaseName}`);
  }
}
