/* eslint-disable @typescript-eslint/no-explicit-any */

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
        <span className="r-code-value">{item.code || '—'}</span>
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

export default function CodingView({ data }: Props) {
  const diagnoses = data?.diagnoses || [];
  const procedures = data?.procedures || [];
  const em = data?.em_calculation;
  const notes = data?.coding_notes || [];
  const queries = data?.queries_needed || [];

  return (
    <div className="renderer-container">
      {/* DIAGNOSES */}
      {diagnoses.length > 0 && (
        <div className="r-section">
          <h4 className="r-section-title">Diagnoses (ICD-10-CM)</h4>
          {diagnoses.map((dx: any, i: number) => (
            <CodeCard key={i} item={dx} type="diagnosis" />
          ))}
        </div>
      )}

      {/* PROCEDURES */}
      {procedures.length > 0 && (
        <div className="r-section">
          <h4 className="r-section-title">Procedures (CPT)</h4>
          {procedures.map((proc: any, i: number) => (
            <CodeCard key={i} item={proc} type="procedure" />
          ))}
        </div>
      )}

      {/* E/M CALCULATION */}
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
              <span>{em.method || '—'}</span>
              <span>{em.problems || '—'}</span>
              <span>{em.data || '—'}</span>
              <span>{em.risk || '—'}</span>
            </div>
          </div>
          <div className="r-em-result">
            <span className="r-label">Level</span>
            <span className="r-badge r-badge-blue">{em.level || '—'}</span>
            <span className="r-label">Code</span>
            <span className="r-code-value r-code-value-sm">{em.code || '—'}</span>
          </div>
        </div>
      )}

      {/* CODING NOTES */}
      {notes.length > 0 && (
        <div className="r-alert r-alert-info">
          <h5>Coding Notes</h5>
          <ul className="r-list">
            {notes.map((n: string, i: number) => <li key={i}>{n}</li>)}
          </ul>
        </div>
      )}

      {/* QUERIES NEEDED */}
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
