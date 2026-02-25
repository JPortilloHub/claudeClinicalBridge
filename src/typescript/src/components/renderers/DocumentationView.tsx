/* eslint-disable @typescript-eslint/no-explicit-any */
import { useState } from 'react';
import Tabs from './Tabs';

interface Props { data: any; }

/* ── Helpers ─────────────────────────────────────────────────── */

/** Check if a string contains a documentation gap marker */
function isDocGap(val: string): boolean {
  return /documentation\s*gap/i.test(val);
}

/** Recursively check if any string value in an object/array contains a documentation gap marker */
function hasDocumentationGaps(obj: any): boolean {
  if (typeof obj === 'string') return isDocGap(obj);
  if (Array.isArray(obj)) return obj.some(item => hasDocumentationGaps(item));
  if (obj && typeof obj === 'object') return Object.values(obj).some(v => hasDocumentationGaps(v));
  return false;
}

/** Convert snake_case key to Title Case */
function formatKey(key: string): string {
  return key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

/** Render a documentation gap indicator */
function DocGapLabel() {
  return (
    <span className="r-doc-gap">
      <span className="r-doc-gap-icon">&#9888;</span> Documentation gap
    </span>
  );
}

/** Render a single value: string (with gap detection), array, or nested object */
function SmartValue({ value }: { value: any }) {
  if (value == null || value === '') return <span className="r-kv-value">{'\u2014'}</span>;

  if (typeof value === 'string') {
    if (isDocGap(value)) return <DocGapLabel />;
    return <>{value}</>;
  }

  if (typeof value === 'boolean') return <>{value ? 'Yes' : 'No'}</>;
  if (typeof value === 'number') return <>{String(value)}</>;

  if (Array.isArray(value)) {
    // Array of strings
    if (value.every(v => typeof v === 'string')) {
      return (
        <ul className="r-list r-list-compact">
          {value.map((item, i) => (
            <li key={i}>{isDocGap(item) ? <DocGapLabel /> : item}</li>
          ))}
        </ul>
      );
    }
    // Array of objects
    return (
      <div className="r-kv-nested">
        {value.map((item, i) => (
          <div key={i} className="r-kv-nested-item">
            {typeof item === 'string' ? (
              isDocGap(item) ? <DocGapLabel /> : <span>{item}</span>
            ) : (
              <KeyValueGrid obj={item} />
            )}
          </div>
        ))}
      </div>
    );
  }

  if (typeof value === 'object') {
    return <KeyValueGrid obj={value} nested />;
  }

  return <>{String(value)}</>;
}

function KeyValueGrid({ obj, nested }: { obj: any; nested?: boolean }) {
  if (!obj || typeof obj !== 'object' || Array.isArray(obj)) return null;
  const entries = Object.entries(obj).filter(([, v]) => v != null && v !== '');
  if (entries.length === 0) return null;
  return (
    <div className={`r-kv-grid ${nested ? 'r-kv-grid-nested' : ''}`}>
      {entries.map(([k, v]) => (
        <div key={k} className="r-kv-row">
          <span className="r-kv-key">{formatKey(k)}</span>
          <span className="r-kv-value"><SmartValue value={v} /></span>
        </div>
      ))}
    </div>
  );
}

function BulletList({ items }: { items: any[] }) {
  if (!items || items.length === 0) return null;
  return (
    <ul className="r-list">
      {items.map((item, i) => (
        <li key={i}>
          {typeof item === 'string' ? (
            isDocGap(item) ? <DocGapLabel /> : item
          ) : typeof item === 'object' && item !== null ? (
            <SmartValue value={item} />
          ) : (
            String(item)
          )}
        </li>
      ))}
    </ul>
  );
}

function StripedList({ items }: { items: string[] }) {
  if (!items || items.length === 0) return null;
  return (
    <div className="r-striped-list">
      {items.map((item, i) => (
        <div key={i} className={`r-striped-row ${i % 2 === 0 ? 'r-striped-even' : 'r-striped-odd'}`}>
          {isDocGap(item) ? <DocGapLabel /> : item}
        </div>
      ))}
    </div>
  );
}

function SectionLabel({ text }: { text: string }) {
  return <h5 className="r-sub-label">{text}</h5>;
}

/** Collapsible section with clickable header and chevron */
function CollapsibleSection({ title, defaultOpen, className, children }: {
  title: string;
  defaultOpen?: boolean;
  className?: string;
  children: React.ReactNode;
}) {
  const [isOpen, setIsOpen] = useState(defaultOpen ?? false);
  return (
    <div className={`r-section ${className || ''}`}>
      <div className="r-collapsible-header" onClick={() => setIsOpen(!isOpen)}>
        <span className="r-collapsible-chevron">{isOpen ? '\u25BE' : '\u25B8'}</span>
        <h4 className="r-section-title" style={{ margin: 0 }}>{title}</h4>
      </div>
      {isOpen && children}
    </div>
  );
}

/* ── Overview tab ─────────────────────────────────────────────── */
function OverviewTab({ data }: Props) {
  const subj = data?.subjective;
  const obj = data?.objective;
  const plan = data?.plan;
  const keyFindings = data?.key_findings;
  const clinicalSummary = data?.clinical_summary;

  // Determine Subjective and Objective completeness based on documentation gaps
  const subjHasGaps = subj ? hasDocumentationGaps(subj) : false;
  const objHasGaps = obj ? hasDocumentationGaps(obj) : false;

  const subjStatus = !subj ? { label: 'Missing', cls: 'r-badge-gray' }
    : subjHasGaps ? { label: 'Not Complete', cls: 'r-badge-yellow' }
    : { label: 'Complete', cls: 'r-badge-green' };

  const objStatus = !obj ? { label: 'Missing', cls: 'r-badge-gray' }
    : objHasGaps ? { label: 'Not Complete', cls: 'r-badge-yellow' }
    : { label: 'Complete', cls: 'r-badge-green' };

  return (
    <div className="r-tab-inner">
      {/* SOAP completeness overview */}
      <div className="r-overview-grid">
        <div className="r-overview-item">
          <span className="r-overview-icon r-soap-s-icon">S</span>
          <span className="r-overview-label">Subjective</span>
          <span className={`r-badge ${subjStatus.cls}`}>{subjStatus.label}</span>
        </div>
        <div className="r-overview-item">
          <span className="r-overview-icon r-soap-o-icon">O</span>
          <span className="r-overview-label">Objective</span>
          <span className={`r-badge ${objStatus.cls}`}>{objStatus.label}</span>
        </div>
        <div className="r-overview-item">
          <span className="r-overview-icon r-soap-p-icon">P</span>
          <span className="r-overview-label">Plan</span>
          <span className={`r-badge ${plan?.length ? 'r-badge-green' : 'r-badge-gray'}`}>
            {plan?.length ? `${plan.length} items` : 'Missing'}
          </span>
        </div>
      </div>

      {/* Key Findings Summary */}
      {(keyFindings || clinicalSummary) && (
        <div className="r-section r-key-findings">
          <h4 className="r-section-title">Key Findings</h4>

          {/* Clinical Problem Representation */}
          {(keyFindings?.clinical_problem || clinicalSummary) && (
            <div className="r-highlight-box r-highlight-box-clinical">
              <span className="r-label">Clinical Problem</span>
              <p className="r-value-clinical">{keyFindings?.clinical_problem || clinicalSummary}</p>
            </div>
          )}

          <div className="r-key-findings-grid">
            {/* Critical Documentation Gaps */}
            {keyFindings?.critical_gaps && keyFindings.critical_gaps.length > 0 && (
              <div className="r-alert r-alert-warning">
                <h5>Critical Documentation Gaps</h5>
                <ol className="r-list r-list-numbered">
                  {keyFindings.critical_gaps.map((gap: string, i: number) => (
                    <li key={i}>{gap}</li>
                  ))}
                </ol>
              </div>
            )}

            {/* Coding Optimization */}
            {keyFindings?.coding_recommendations && keyFindings.coding_recommendations.length > 0 && (
              <div className="r-alert r-alert-info">
                <h5>Coding Optimization</h5>
                <ul className="r-list">
                  {keyFindings.coding_recommendations.map((rec: string, i: number) => (
                    <li key={i}>{rec}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      )}

    </div>
  );
}

/* ── Details tab ──────────────────────────────────────────────── */
function DetailsTab({ data }: Props) {
  const subj = data?.subjective;
  const obj = data?.objective;
  const assess = data?.assessment;
  const plan = data?.plan;

  return (
    <div className="r-tab-inner">
      {/* SUBJECTIVE */}
      {subj && (
        <CollapsibleSection title="Subjective" className="r-soap-s">
          {subj.chief_complaint && (
            <div className="r-highlight-box">
              <span className="r-label">Chief Complaint</span>
              <p className="r-value-lg">{subj.chief_complaint}</p>
            </div>
          )}

          {subj.hpi && (
            <>
              <SectionLabel text="History of Present Illness" />
              <KeyValueGrid obj={subj.hpi} />
            </>
          )}

          {subj.ros && typeof subj.ros === 'object' && (
            <>
              <SectionLabel text="Review of Systems" />
              <KeyValueGrid obj={subj.ros} />
            </>
          )}

          {subj.pmh && subj.pmh.length > 0 && (
            <>
              <SectionLabel text="Past Medical History" />
              <StripedList items={subj.pmh} />
            </>
          )}

          {subj.psh && (
            <>
              <SectionLabel text="Past Surgical History" />
              {typeof subj.psh === 'string' && isDocGap(subj.psh) ? <DocGapLabel /> : <SmartValue value={subj.psh} />}
            </>
          )}

          {subj.social_history && typeof subj.social_history === 'object' && (
            <>
              <SectionLabel text="Social History" />
              <KeyValueGrid obj={subj.social_history} />
            </>
          )}

          {subj.family_history && (
            <>
              <SectionLabel text="Family History" />
              {typeof subj.family_history === 'string' && isDocGap(subj.family_history) ? <DocGapLabel /> : <SmartValue value={subj.family_history} />}
            </>
          )}

          <div className="r-inline-lists">
            {subj.medications && subj.medications.length > 0 && (
              <div className="r-inline-list-item">
                <SectionLabel text="Medications" />
                <StripedList items={subj.medications} />
              </div>
            )}
            {subj.allergies && subj.allergies.length > 0 && (
              <div className="r-inline-list-item">
                <SectionLabel text="Allergies" />
                <BulletList items={subj.allergies} />
              </div>
            )}
          </div>
        </CollapsibleSection>
      )}

      {/* OBJECTIVE */}
      {obj && (
        <CollapsibleSection title="Objective" className="r-soap-o">
          {obj.vitals && typeof obj.vitals === 'object' && (
            <>
              <SectionLabel text="Vital Signs" />
              <div className="r-vitals-grid">
                {Object.entries(obj.vitals).filter(([, v]) => v != null && v !== '').map(([k, v]) => (
                  <div key={k} className="r-vital-item">
                    <span className="r-vital-label">{formatKey(k)}</span>
                    <span className="r-vital-value">
                      {typeof v === 'string' && isDocGap(v) ? <DocGapLabel /> : String(v)}
                    </span>
                  </div>
                ))}
              </div>
            </>
          )}

          {obj.physical_exam && typeof obj.physical_exam === 'object' && (
            <>
              <SectionLabel text="Physical Examination" />
              <KeyValueGrid obj={obj.physical_exam} />
            </>
          )}

          {obj.labs && obj.labs.length > 0 && (
            <>
              <SectionLabel text="Laboratory Results" />
              <BulletList items={obj.labs} />
            </>
          )}

          {obj.imaging && obj.imaging.length > 0 && (
            <>
              <SectionLabel text="Imaging" />
              <BulletList items={obj.imaging} />
            </>
          )}
        </CollapsibleSection>
      )}

      {/* ASSESSMENT */}
      {assess && Array.isArray(assess) && assess.length > 0 && (
        <CollapsibleSection title="Assessment" className="r-soap-a">
          {assess.map((dx: any, i: number) => (
            <div key={i} className="r-card">
              <div className="r-card-header">
                {(dx.icd10_hint || dx.icd10_code) && (
                  <span className="r-badge r-badge-blue">{dx.icd10_hint || dx.icd10_code}</span>
                )}
                <strong>{dx.diagnosis || `Diagnosis ${i + 1}`}</strong>
              </div>
              {dx.severity && <p className="r-card-note"><strong>Severity:</strong> {dx.severity}</p>}
              {dx.clinical_reasoning && (
                <p className="r-card-detail">{dx.clinical_reasoning}</p>
              )}
              {dx.impact_on_primary_diagnosis && (
                <p className="r-card-note"><strong>Impact:</strong> {dx.impact_on_primary_diagnosis}</p>
              )}
              {dx.surgical_relevance && (
                <p className="r-card-note"><strong>Surgical Relevance:</strong> {dx.surgical_relevance}</p>
              )}
              <div className="r-pertinents">
                {dx.pertinent_positives && dx.pertinent_positives.length > 0 && (
                  <div className="r-pertinent-group">
                    {dx.pertinent_positives.map((p: string, j: number) => (
                      <span key={j} className="r-pertinent r-pertinent-pos">+ {p}</span>
                    ))}
                  </div>
                )}
                {dx.pertinent_negatives && dx.pertinent_negatives.length > 0 && (
                  <div className="r-pertinent-group">
                    {dx.pertinent_negatives.map((p: string, j: number) => (
                      <span key={j} className="r-pertinent r-pertinent-neg">- {p}</span>
                    ))}
                  </div>
                )}
              </div>
              {dx.differential_diagnosis_considered && Array.isArray(dx.differential_diagnosis_considered) && (
                <div style={{ marginTop: '10px' }}>
                  <strong style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Differential Diagnoses:</strong>
                  {dx.differential_diagnosis_considered.map((dd: any, j: number) => (
                    <div key={j} className="r-kv-row" style={{ padding: '4px 0', fontSize: '12px' }}>
                      <span className="r-kv-key" style={{ minWidth: '120px' }}>{dd.diagnosis}</span>
                      <span className={`r-badge ${dd.likelihood?.toLowerCase() === 'ruled out' ? 'r-badge-green' : 'r-badge-yellow'}`} style={{ fontSize: '10px' }}>
                        {dd.likelihood}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </CollapsibleSection>
      )}

      {/* PLAN */}
      {plan && Array.isArray(plan) && plan.length > 0 && (
        <CollapsibleSection title="Plan" className="r-soap-p">
          {plan.map((item: any, i: number) => (
            <div key={i} className="r-card">
              <div className="r-card-header">
                <strong>{item.diagnosis || `Plan ${i + 1}`}</strong>
              </div>
              {item.actions && <BulletList items={item.actions} />}
            </div>
          ))}
        </CollapsibleSection>
      )}
    </div>
  );
}

/* ── Documentation Gaps (collapsible cards) ───────────────────── */
function GapCard({ gap, defaultOpen }: { gap: any; defaultOpen?: boolean }) {
  const [isOpen, setIsOpen] = useState(defaultOpen ?? false);
  const missingCount = Array.isArray(gap.missing_elements) ? gap.missing_elements.length : 0;

  return (
    <div className={`r-gap-card ${isOpen ? 'r-gap-card-open' : ''}`}>
      <div className="r-gap-card-header" onClick={() => setIsOpen(!isOpen)}>
        <span className="r-gap-card-chevron">{isOpen ? '\u25BE' : '\u25B8'}</span>
        <span className="r-gap-card-title">{gap.category || 'Documentation Gap'}</span>
        {missingCount > 0 && (
          <span className="r-badge r-badge-yellow">{missingCount} missing</span>
        )}
      </div>
      {isOpen && (
        <div className="r-gap-card-body">
          {Array.isArray(gap.missing_elements) && gap.missing_elements.length > 0 && (
            <div className="r-gap-card-missing">
              <strong>Missing Elements:</strong>
              <ul className="r-list r-list-compact">
                {gap.missing_elements.map((el: string, j: number) => (
                  <li key={j}>{el}</li>
                ))}
              </ul>
            </div>
          )}
          {gap.impact && (
            <div className="r-gap-card-impact">
              <strong>Impact:</strong> {gap.impact}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function DocumentationGapsSection({ gaps }: { gaps: any[] }) {
  return (
    <div className="r-doc-gaps-section">
      {gaps.map((gap, i) => (
        <GapCard key={i} gap={gap} defaultOpen={i === 0} />
      ))}
    </div>
  );
}

/* ── Coding Hints Section ─────────────────────────────────────── */
function CodingHintsSection({ hints }: { hints: any }) {
  if (!hints || typeof hints !== 'object') return null;

  const simpleFields: [string, string][] = [];
  const mdmElements = hints.mdm_elements;
  const diagnosisCodes = hints.diagnosis_codes;
  const procedureCodes = hints.procedure_codes_anticipated;
  const qualityMeasures = hints.quality_measures;
  const complianceConsiderations = hints.compliance_considerations;

  // Collect simple string fields
  for (const [k, v] of Object.entries(hints)) {
    if (['mdm_elements', 'diagnosis_codes', 'procedure_codes_anticipated', 'quality_measures', 'compliance_considerations'].includes(k)) continue;
    if (typeof v === 'string') {
      simpleFields.push([k, v]);
    }
  }

  return (
    <div className="r-coding-hints">
      {/* Simple key-value fields */}
      {simpleFields.length > 0 && (
        <div className="r-kv-grid">
          {simpleFields.map(([k, v]) => (
            <div key={k} className="r-kv-row">
              <span className="r-kv-key">{formatKey(k)}</span>
              <span className="r-kv-value">{v}</span>
            </div>
          ))}
        </div>
      )}

      {/* MDM Elements */}
      {mdmElements && typeof mdmElements === 'object' && (
        <div style={{ marginTop: '12px' }}>
          <SectionLabel text="MDM Elements" />
          <div className="r-kv-grid">
            {Object.entries(mdmElements).map(([k, v]) => (
              <div key={k} className="r-kv-row">
                <span className="r-kv-key">{formatKey(k)}</span>
                <span className="r-kv-value">{String(v)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Diagnosis Codes */}
      {Array.isArray(diagnosisCodes) && diagnosisCodes.length > 0 && (
        <div style={{ marginTop: '12px' }}>
          <SectionLabel text="Diagnosis Codes" />
          {diagnosisCodes.map((dc: any, i: number) => (
            <div key={i} className="r-code-hint-item">
              <span className="r-badge r-badge-blue">{dc.code}</span>
              <span className="r-code-hint-desc">{dc.description}</span>
              {(dc.note || dc.specificity) && (
                <span className="r-code-hint-note">{dc.note || dc.specificity}</span>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Procedure Codes */}
      {Array.isArray(procedureCodes) && procedureCodes.length > 0 && (
        <div style={{ marginTop: '12px' }}>
          <SectionLabel text="Procedure Codes" />
          {procedureCodes.map((pc: any, i: number) => (
            <div key={i} className="r-code-hint-item">
              <span className="r-badge r-badge-blue">{pc.code}</span>
              <span className="r-code-hint-desc">{pc.description}</span>
              {pc.note && <span className="r-code-hint-note">{pc.note}</span>}
            </div>
          ))}
        </div>
      )}

      {/* Quality Measures */}
      {Array.isArray(qualityMeasures) && qualityMeasures.length > 0 && (
        <div style={{ marginTop: '12px' }}>
          <SectionLabel text="Quality Measures" />
          {qualityMeasures.map((qm: any, i: number) => {
            const statusLower = (qm.status || '').toLowerCase();
            const isMet = statusLower.startsWith('met');
            const isPartial = statusLower.includes('partial');
            const icon = isMet ? '\u2713' : isPartial ? '\u26A0' : '\u2717';
            const cls = isMet ? 'r-qm-met' : isPartial ? 'r-qm-partial' : 'r-qm-not-met';
            return (
              <div key={i} className={`r-qm-item ${cls}`}>
                <span className="r-qm-icon">{icon}</span>
                <span className="r-qm-measure">{qm.measure}</span>
                <span className="r-qm-status">{qm.status}</span>
              </div>
            );
          })}
        </div>
      )}

      {/* Compliance Considerations */}
      {Array.isArray(complianceConsiderations) && complianceConsiderations.length > 0 && (
        <div style={{ marginTop: '12px' }}>
          <SectionLabel text="Compliance Considerations" />
          <StripedList items={complianceConsiderations} />
        </div>
      )}
    </div>
  );
}

/* ── Issues tab ───────────────────────────────────────────────── */
function IssuesTab({ data }: Props) {
  const gaps = data?.documentation_gaps || [];
  const hints = data?.coding_hints;

  if (gaps.length === 0 && !hints) {
    return (
      <div className="r-tab-inner">
        <div className="r-empty-success">No documentation issues found</div>
      </div>
    );
  }

  return (
    <div className="r-tab-inner">
      {gaps.length > 0 && (
        <div className="r-section">
          <h4 className="r-section-title">Documentation Gaps</h4>
          <DocumentationGapsSection gaps={gaps} />
        </div>
      )}
      {hints && (
        <div className="r-section">
          <h4 className="r-section-title">Coding Hints</h4>
          <CodingHintsSection hints={hints} />
        </div>
      )}
    </div>
  );
}

/* ── Main component ───────────────────────────────────────────── */
export default function DocumentationView({ data }: Props) {
  if (!data) return null;

  const gaps = data?.documentation_gaps || [];

  return (
    <div className="renderer-container">
      <Tabs tabs={[
        { label: 'Overview', content: <OverviewTab data={data} /> },
        { label: 'Details', content: <DetailsTab data={data} /> },
        {
          label: 'Issues',
          count: gaps.length,
          content: (gaps.length > 0 || data?.coding_hints) ? <IssuesTab data={data} /> : null,
        },
      ]} />
    </div>
  );
}
