/* eslint-disable @typescript-eslint/no-explicit-any */
import Tabs from './Tabs';

interface Props { data: any; }

function confidenceClass(c: string | undefined): string {
  if (!c) return 'r-badge-gray';
  const l = c.toLowerCase();
  if (l === 'high') return 'r-badge-green';
  if (l === 'medium' || l === 'moderate') return 'r-badge-yellow';
  return 'r-badge-red';
}

function CodeCard({ item, type }: { item: any; type: 'diagnosis' | 'procedure' }) {
  return (
    <div className="r-card r-code-card">
      <div className="r-code-card-top">
        <span className="r-code-value">{item.code || '\u2014'}</span>
        <div className="r-code-info">
          <strong>{item.description || 'No description'}</strong>
          <div className="r-code-badges">
            {type === 'diagnosis' && item.sequencing && (
              <span className={`r-badge ${item.sequencing === 'primary' ? 'r-badge-blue' : 'r-badge-gray'}`}>
                {item.sequencing}
              </span>
            )}
            {item.confidence && (
              <span className={`r-badge ${confidenceClass(item.confidence)}`}>
                {item.confidence}
              </span>
            )}
            {item.modifiers && item.modifiers.length > 0 && item.modifiers.map((m: string, i: number) => (
              <span key={i} className="r-badge r-badge-gray">Mod: {m}</span>
            ))}
          </div>
        </div>
      </div>
      {item.rationale && <p className="r-card-detail">{item.rationale}</p>}
      {item.specificity_check && <p className="r-card-note">{item.specificity_check}</p>}
    </div>
  );
}

/* ── Overview tab ─────────────────────────────────────────────── */
function OverviewTab({ data }: Props) {
  const diagnoses = data?.diagnoses || [];
  const procedures = data?.procedures || [];
  const em = data?.em_calculation;

  return (
    <div className="r-tab-inner">
      {diagnoses.length > 0 && (
        <div className="r-section">
          <h4 className="r-section-title">Diagnoses (ICD-10-CM)</h4>
          <div className="r-code-table">
            <div className="r-code-table-header">
              <span>Code</span>
              <span>Description</span>
              <span>Type</span>
              <span>Confidence</span>
            </div>
            {diagnoses.map((dx: any, i: number) => (
              <div key={i} className="r-code-table-row">
                <span className="r-code-value r-code-value-sm">{dx.code || '\u2014'}</span>
                <span>{dx.description || '\u2014'}</span>
                <span>
                  {dx.sequencing && (
                    <span className={`r-badge ${dx.sequencing === 'primary' ? 'r-badge-blue' : 'r-badge-gray'}`}>
                      {dx.sequencing}
                    </span>
                  )}
                </span>
                <span>
                  {dx.confidence && (
                    <span className={`r-badge ${confidenceClass(dx.confidence)}`}>{dx.confidence}</span>
                  )}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {procedures.length > 0 && (
        <div className="r-section">
          <h4 className="r-section-title">Procedures (CPT)</h4>
          <div className="r-code-table">
            <div className="r-code-table-header">
              <span>Code</span>
              <span>Description</span>
              <span>Confidence</span>
            </div>
            {procedures.map((proc: any, i: number) => (
              <div key={i} className="r-code-table-row">
                <span className="r-code-value r-code-value-sm">{proc.code || '\u2014'}</span>
                <span>{proc.description || '\u2014'}</span>
                <span>
                  {proc.confidence && (
                    <span className={`r-badge ${confidenceClass(proc.confidence)}`}>{proc.confidence}</span>
                  )}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {em && (
        <div className="r-section">
          <h4 className="r-section-title">E/M Level</h4>
          <div className="r-em-result">
            <span className="r-label">Level</span>
            <span className="r-badge r-badge-blue">{em.level || '\u2014'}</span>
            <span className="r-label">Code</span>
            <span className="r-code-value r-code-value-sm">{em.code || '\u2014'}</span>
          </div>
        </div>
      )}
    </div>
  );
}

/* ── Details tab ──────────────────────────────────────────────── */
function DetailsTab({ data }: Props) {
  const diagnoses = data?.diagnoses || [];
  const procedures = data?.procedures || [];
  const em = data?.em_calculation;

  return (
    <div className="r-tab-inner">
      {diagnoses.length > 0 && (
        <div className="r-section">
          <h4 className="r-section-title">Diagnosis Details</h4>
          {diagnoses.map((dx: any, i: number) => (
            <CodeCard key={i} item={dx} type="diagnosis" />
          ))}
        </div>
      )}

      {procedures.length > 0 && (
        <div className="r-section">
          <h4 className="r-section-title">Procedure Details</h4>
          {procedures.map((proc: any, i: number) => (
            <CodeCard key={i} item={proc} type="procedure" />
          ))}
        </div>
      )}

      {em && (
        <div className="r-section">
          <h4 className="r-section-title">E/M Level Calculation</h4>
          <div className="r-em-table">
            <div className="r-em-row r-em-header">
              <span>Method</span>
              <span>Problems</span>
              <span>Data</span>
              <span>Risk</span>
            </div>
            <div className="r-em-row">
              <span>{em.method || '\u2014'}</span>
              <span>{em.problems || '\u2014'}</span>
              <span>{em.data || '\u2014'}</span>
              <span>{em.risk || '\u2014'}</span>
            </div>
          </div>
          <div className="r-em-result">
            <span className="r-label">Level</span>
            <span className="r-badge r-badge-blue">{em.level || '\u2014'}</span>
            <span className="r-label">Code</span>
            <span className="r-code-value r-code-value-sm">{em.code || '\u2014'}</span>
          </div>
        </div>
      )}
    </div>
  );
}

/* ── Issues tab ───────────────────────────────────────────────── */
function IssuesTab({ data }: Props) {
  const notes = data?.coding_notes || [];
  const queries = data?.queries_needed || [];

  if (notes.length === 0 && queries.length === 0) {
    return (
      <div className="r-tab-inner">
        <div className="r-empty-success">No coding issues or queries</div>
      </div>
    );
  }

  return (
    <div className="r-tab-inner">
      {notes.length > 0 && (
        <div className="r-alert r-alert-info">
          <h5>Coding Notes</h5>
          <ul className="r-list">
            {notes.map((n: string, i: number) => <li key={i}>{n}</li>)}
          </ul>
        </div>
      )}
      {queries.length > 0 && (
        <div className="r-alert r-alert-warning">
          <h5>Queries for Provider</h5>
          <ul className="r-list">
            {queries.map((q: string, i: number) => <li key={i}>{q}</li>)}
          </ul>
        </div>
      )}
    </div>
  );
}

/* ── Main component ───────────────────────────────────────────── */
export default function CodingView({ data }: Props) {
  if (!data) return null;

  const queries = data?.queries_needed || [];
  const notes = data?.coding_notes || [];
  const issueCount = queries.length + notes.length;

  return (
    <div className="renderer-container">
      <Tabs tabs={[
        { label: 'Overview', content: <OverviewTab data={data} /> },
        { label: 'Details', content: <DetailsTab data={data} /> },
        {
          label: 'Issues',
          count: issueCount,
          content: issueCount > 0 ? <IssuesTab data={data} /> : null,
        },
      ]} />
    </div>
  );
}
