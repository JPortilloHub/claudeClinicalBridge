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
    const data = result.success ? result.data : json as Record<string, unknown>;

    const kpis: KPIItem[] = [];
    const subjective = (data as Record<string, unknown>)?.subjective as Record<string, unknown> | undefined;
    const chiefComplaint = subjective?.chief_complaint as string | undefined;
    if (chiefComplaint) {
      kpis.push({ label: 'Chief Complaint', value: chiefComplaint });
    }

    const assessment = (data as Record<string, unknown>)?.assessment;
    if (Array.isArray(assessment)) {
      kpis.push({ label: 'Diagnoses', value: assessment.length, color: 'blue' });
    }

    const gaps = (data as Record<string, unknown>)?.documentation_gaps;
    if (Array.isArray(gaps) && gaps.length > 0) {
      kpis.push({ label: 'Doc Gaps', value: gaps.length, color: 'yellow' });
    } else {
      kpis.push({ label: 'Doc Gaps', value: 0, color: 'green' });
    }

    const plan = (data as Record<string, unknown>)?.plan;
    if (Array.isArray(plan)) {
      kpis.push({ label: 'Plan Items', value: plan.length, color: 'blue' });
    }

    addTruncationWarning(kpis, wasTruncated);

    const summary = chiefComplaint
      ? `SOAP note for: ${chiefComplaint}`
      : 'Clinical documentation structured as SOAP note';

    const d = data as Record<string, unknown>;
    return {
      status: 'completed',
      summary: wasTruncated ? summary + ' (partial output)' : summary,
      kpis,
      sections: [
        { title: 'Subjective', content: d?.subjective },
        { title: 'Objective', content: d?.objective },
        { title: 'Assessment', content: d?.assessment },
        { title: 'Plan', content: d?.plan },
        { title: 'Documentation Gaps', content: d?.documentation_gaps },
        { title: 'Coding Hints', content: d?.coding_hints },
      ].filter(s => s.content != null),
      raw: json,
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
    return buildFallback(raw, 'Unable to parse coding output');
  }

  try {
    const result = CodingSchema.safeParse(json);
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const data = (result.success ? result.data : json) as any;

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
      raw: json,
    };
  } catch (e) {
    return buildFallback(raw, e instanceof Error ? e.message : 'Parse error');
  }
}

/* ------------------------------------------------------------------ */
/*  Compliance Validation parser                                       */
/* ------------------------------------------------------------------ */

export function parseCompliance(raw: string | object): PhaseViewModel {
  const [json, wasTruncated] = safeParse(raw);
  if (json === null || typeof json !== 'object') {
    return buildFallback(raw, 'Unable to parse compliance output');
  }

  try {
    const result = ComplianceSchema.safeParse(json);
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const data = (result.success ? result.data : json) as any;

    const kpis: KPIItem[] = [];
    const status = data?.overall_status;
    const statusLower = (status || '').toLowerCase();
    const statusColor = statusLower === 'pass' ? 'green' as const
      : statusLower === 'needs_review' ? 'yellow' as const
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

    if (data?.risk_level) {
      kpis.push({ label: 'Risk', value: data.risk_level, color: statusColor });
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
      raw: json,
    };
  } catch (e) {
    return buildFallback(raw, e instanceof Error ? e.message : 'Parse error');
  }
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
    return buildFallback(raw, 'Unable to parse quality assurance output');
  }

  try {
    const result = QualitySchema.safeParse(json);
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const data = (result.success ? result.data : json) as any;

    const kpis: KPIItem[] = [];

    if (data?.overall_quality) {
      const q = data.overall_quality.toLowerCase();
      kpis.push({
        label: 'Quality',
        value: data.overall_quality.replace(/_/g, ' '),
        color: q === 'approved' ? 'green' : q === 'needs_revision' ? 'yellow' : 'red',
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
      raw: json,
    };
  } catch (e) {
    return buildFallback(raw, e instanceof Error ? e.message : 'Parse error');
  }
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
