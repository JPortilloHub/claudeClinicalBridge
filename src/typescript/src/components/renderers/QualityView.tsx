/* eslint-disable @typescript-eslint/no-explicit-any */
import Tabs from './Tabs';

interface Props { data: any; }

function ScoreBar({ label, score }: { label: string; score: number }) {
  const pct = Math.min(100, Math.max(0, score));
  const color = pct >= 90 ? 'var(--success)' : pct >= 70 ? 'var(--warning)' : 'var(--danger)';
  return (
    <div className="r-dimension-row">
      <span className="r-dimension-label">{label.replace(/_/g, ' ')}</span>
      <div className="r-progress-bar r-progress-bar-sm">
        <div className="r-progress-fill" style={{ width: `${pct}%`, background: color }} />
      </div>
      <span className="r-dimension-score">{score}</span>
    </div>
  );
}

function qualityStatusColor(s: string | undefined): string {
  if (!s) return '';
  const l = s.toLowerCase();
  if (l === 'approved') return 'r-status-pass';
  if (l === 'needs_revision') return 'r-status-warning';
  return 'r-status-fail';
}

/* ── Overview tab ─────────────────────────────────────────────── */
function OverviewTab({ data }: Props) {
  const status = data?.overall_quality;
  const score = data?.quality_score;
  const ready = data?.ready_for_submission;
  const dims = data?.dimensions;

  return (
    <div className="r-tab-inner">
      {/* Quality header */}
      <div className={`r-status-banner ${qualityStatusColor(status)}`}>
        <div className="r-status-banner-items">
          <div className="r-status-item">
            <span className="r-status-label">Quality</span>
            <span className="r-status-value">{status?.replace(/_/g, ' ') || 'Unknown'}</span>
          </div>
          {score != null && (
            <div className="r-status-item">
              <span className="r-status-label">Score</span>
              <span className="r-status-value">{score}/100</span>
            </div>
          )}
          <div className="r-status-item">
            <span className="r-status-label">Ready</span>
            <span className="r-status-value">{ready ? 'Yes' : 'No'}</span>
          </div>
        </div>
      </div>

      {/* Dimension scores */}
      {dims && typeof dims === 'object' && (
        <div className="r-section">
          <h4 className="r-section-title">Quality Dimensions</h4>
          <div className="r-dimensions">
            {Object.entries(dims).map(([key, dim]: [string, any]) => (
              <div key={key}>
                <ScoreBar label={key} score={dim?.score ?? 0} />
                {dim?.issues && dim.issues.length > 0 && (
                  <ul className="r-list r-list-compact r-dimension-issues">
                    {dim.issues.map((issue: string, i: number) => <li key={i}>{issue}</li>)}
                  </ul>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

/* ── Details tab ──────────────────────────────────────────────── */
function DetailsTab({ data }: Props) {
  const improvements = data?.improvements || [];
  const trace = data?.traceability;

  return (
    <div className="r-tab-inner">
      {/* Improvements */}
      {improvements.length > 0 && (
        <div className="r-section">
          <h4 className="r-section-title">Suggested Improvements</h4>
          <ol className="r-list r-list-numbered">
            {improvements.map((item: string, i: number) => <li key={i}>{item}</li>)}
          </ol>
        </div>
      )}

      {/* Traceability */}
      {trace && (
        <div className="r-section">
          <h4 className="r-section-title">Traceability</h4>
          <div className="r-checklist">
            <div className="r-checklist-item">
              <span className={trace.all_codes_traceable ? 'r-icon-pass' : 'r-icon-fail'}>
                {trace.all_codes_traceable ? '\u2713' : '\u2717'}
              </span>
              <span>All codes traceable to source documentation</span>
            </div>
          </div>
          {trace.untraceable_items && trace.untraceable_items.length > 0 && (
            <div className="r-alert r-alert-danger" style={{ marginTop: '8px' }}>
              <h5>Untraceable Items</h5>
              <ul className="r-list">
                {trace.untraceable_items.map((item: string, i: number) => <li key={i}>{item}</li>)}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/* ── Issues tab ───────────────────────────────────────────────── */
function IssuesTab({ data }: Props) {
  const critical = data?.critical_issues || [];
  const warnings = data?.warnings || [];

  if (critical.length === 0 && warnings.length === 0) {
    return (
      <div className="r-tab-inner">
        <div className="r-empty-success">No issues found</div>
      </div>
    );
  }

  return (
    <div className="r-tab-inner">
      {/* Critical issues */}
      {critical.length > 0 && (
        <div className="r-alert r-alert-danger">
          <h5>Critical Issues</h5>
          <ul className="r-list">
            {critical.map((issue: string, i: number) => <li key={i}>{issue}</li>)}
          </ul>
        </div>
      )}

      {/* Warnings */}
      {warnings.length > 0 && (
        <div className="r-section">
          <h4 className="r-section-title">Warnings</h4>
          {warnings.map((w: any, i: number) => (
            <div key={i} className="r-card r-issue-card r-issue-warning">
              <div className="r-card-header">
                {w.category && <span className="r-badge r-badge-yellow">{w.category}</span>}
              </div>
              <p className="r-card-detail">{w.description || (typeof w === 'string' ? w : JSON.stringify(w))}</p>
              {w.recommendation && (
                <p className="r-card-remediation"><strong>Recommendation:</strong> {w.recommendation}</p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* ── Main component ───────────────────────────────────────────── */
export default function QualityView({ data }: Props) {
  if (!data) return null;

  const critical = data?.critical_issues || [];
  const warnings = data?.warnings || [];
  const issueCount = critical.length + warnings.length;

  return (
    <div className="renderer-container">
      <Tabs tabs={[
        { label: 'Overview', content: <OverviewTab data={data} /> },
        { label: 'Details', content: <DetailsTab data={data} /> },
        {
          label: 'Issues',
          count: issueCount,
          content: <IssuesTab data={data} />,
        },
      ]} />
    </div>
  );
}
