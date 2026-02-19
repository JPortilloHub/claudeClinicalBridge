/* eslint-disable @typescript-eslint/no-explicit-any */
import Tabs from './Tabs';

interface Props { data: any; }

function statusColor(s: string | undefined): string {
  if (!s) return '';
  const l = s.toLowerCase();
  if (l === 'pass' || l === 'low') return 'r-status-pass';
  if (l === 'needs_review' || l === 'medium') return 'r-status-warning';
  return 'r-status-fail';
}

function severityBadge(s: string | undefined): string {
  if (!s) return 'r-badge-gray';
  const l = s.toLowerCase();
  if (l === 'critical') return 'r-badge-red';
  if (l === 'warning') return 'r-badge-yellow';
  return 'r-badge-blue';
}

function ProgressBar({ value, max = 100 }: { value: number; max?: number }) {
  const pct = Math.min(100, Math.max(0, (value / max) * 100));
  const color = pct >= 90 ? 'var(--success)' : pct >= 70 ? 'var(--warning)' : 'var(--danger)';
  return (
    <div className="r-progress-bar">
      <div className="r-progress-fill" style={{ width: `${pct}%`, background: color }} />
      <span className="r-progress-label">{value}/{max}</span>
    </div>
  );
}

/* ── Overview tab ─────────────────────────────────────────────── */
function OverviewTab({ data }: Props) {
  const status = data?.overall_status;
  const risk = data?.risk_level;
  const score = data?.audit_readiness_score;
  const issues = data?.compliance_issues || [];

  return (
    <div className="r-tab-inner">
      {/* Status banner */}
      <div className={`r-status-banner ${statusColor(status)}`}>
        <div className="r-status-banner-items">
          <div className="r-status-item">
            <span className="r-status-label">Overall</span>
            <span className="r-status-value">{status?.replace(/_/g, ' ') || 'Unknown'}</span>
          </div>
          <div className="r-status-item">
            <span className="r-status-label">Risk Level</span>
            <span className="r-status-value">{risk || 'Unknown'}</span>
          </div>
          {score != null && (
            <div className="r-status-item">
              <span className="r-status-label">Audit Score</span>
              <span className="r-status-value">{score}/100</span>
            </div>
          )}
        </div>
      </div>

      {/* Audit readiness */}
      {score != null && (
        <div className="r-section">
          <h4 className="r-section-title">Audit Readiness</h4>
          <ProgressBar value={score} />
        </div>
      )}

      {/* Issue count summary */}
      {issues.length > 0 && (
        <div className="r-section">
          <h4 className="r-section-title">Issue Summary</h4>
          <div className="r-issue-summary-row">
            {(['critical', 'warning', 'info'] as const).map(severity => {
              const count = issues.filter((i: any) => i.severity === severity).length;
              if (count === 0) return null;
              return (
                <div key={severity} className="r-issue-summary-item">
                  <span className={`r-badge ${severityBadge(severity)}`}>{severity}</span>
                  <span className="r-issue-summary-count">{count}</span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {issues.length === 0 && (
        <div className="r-empty-success">No compliance issues found</div>
      )}
    </div>
  );
}

/* ── Details tab ──────────────────────────────────────────────── */
function DetailsTab({ data }: Props) {
  const codeVals = data?.code_validations || [];
  const emVal = data?.em_validation;
  const payer = data?.payer_checks;

  return (
    <div className="r-tab-inner">
      {/* Code validations */}
      {codeVals.length > 0 && (
        <div className="r-section">
          <h4 className="r-section-title">Code Validations</h4>
          {codeVals.map((cv: any, i: number) => (
            <div key={i} className="r-validation-row">
              <span className={cv.status === 'pass' ? 'r-icon-pass' : 'r-icon-fail'}>
                {cv.status === 'pass' ? '\u2713' : '\u2717'}
              </span>
              <span className="r-code-value r-code-value-sm">{cv.code}</span>
              <span className="r-validation-text">
                {cv.documentation_support || (cv.issues && cv.issues.join('; ')) || cv.status}
              </span>
            </div>
          ))}
        </div>
      )}

      {/* E/M validation */}
      {emVal && (
        <div className="r-section">
          <h4 className="r-section-title">E/M Validation</h4>
          <div className="r-em-validation">
            <div className="r-em-compare">
              <div className="r-em-compare-item">
                <span className="r-label">Documented</span>
                <span className="r-code-value r-code-value-sm">{emVal.documented_level || '\u2014'}</span>
              </div>
              <span className="r-em-arrow">{'\u2192'}</span>
              <div className="r-em-compare-item">
                <span className="r-label">Supported</span>
                <span className="r-code-value r-code-value-sm">{emVal.supported_level || '\u2014'}</span>
              </div>
              <span className={`r-badge ${emVal.status === 'pass' ? 'r-badge-green' : 'r-badge-red'}`}>
                {emVal.status || '\u2014'}
              </span>
            </div>
            {emVal.issues && emVal.issues.length > 0 && (
              <ul className="r-list r-list-compact">
                {emVal.issues.map((issue: string, i: number) => <li key={i}>{issue}</li>)}
              </ul>
            )}
          </div>
        </div>
      )}

      {/* Payer checks */}
      {payer && (
        <div className="r-section">
          <h4 className="r-section-title">Payer Checks</h4>
          <div className="r-checklist">
            <div className="r-checklist-item">
              <span className={payer.prior_auth_required ? 'r-icon-warn' : 'r-icon-pass'}>
                {payer.prior_auth_required ? '!' : '\u2713'}
              </span>
              <span>Prior Authorization {payer.prior_auth_required ? 'Required' : 'Not Required'}</span>
            </div>
            <div className="r-checklist-item">
              <span className={payer.documentation_complete ? 'r-icon-pass' : 'r-icon-fail'}>
                {payer.documentation_complete ? '\u2713' : '\u2717'}
              </span>
              <span>Documentation {payer.documentation_complete ? 'Complete' : 'Incomplete'}</span>
            </div>
          </div>
          {payer.missing_elements && payer.missing_elements.length > 0 && (
            <div className="r-alert r-alert-warning" style={{ marginTop: '8px' }}>
              <h5>Missing Elements</h5>
              <ul className="r-list">
                {payer.missing_elements.map((el: string, i: number) => <li key={i}>{el}</li>)}
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
  const issues = data?.compliance_issues || [];

  const sortedIssues = [...issues].sort((a: any, b: any) => {
    const order: Record<string, number> = { critical: 0, warning: 1, info: 2 };
    return (order[a.severity] ?? 3) - (order[b.severity] ?? 3);
  });

  if (sortedIssues.length === 0) {
    return (
      <div className="r-tab-inner">
        <div className="r-empty-success">No compliance issues found</div>
      </div>
    );
  }

  return (
    <div className="r-tab-inner">
      {sortedIssues.map((issue: any, i: number) => (
        <div key={i} className={`r-card r-issue-card r-issue-${issue.severity || 'info'}`}>
          <div className="r-card-header">
            <span className={`r-badge ${severityBadge(issue.severity)}`}>{issue.severity}</span>
            {issue.category && <span className="r-badge r-badge-gray">{issue.category?.replace(/_/g, ' ')}</span>}
          </div>
          <p className="r-card-detail">{issue.description}</p>
          {issue.regulatory_reference && (
            <p className="r-card-note"><strong>Reference:</strong> {issue.regulatory_reference}</p>
          )}
          {issue.remediation && (
            <p className="r-card-remediation"><strong>Fix:</strong> {issue.remediation}</p>
          )}
        </div>
      ))}
    </div>
  );
}

/* ── Main component ───────────────────────────────────────────── */
export default function ComplianceView({ data }: Props) {
  if (!data) return null;

  const issues = data?.compliance_issues || [];

  return (
    <div className="renderer-container">
      <Tabs tabs={[
        { label: 'Overview', content: <OverviewTab data={data} /> },
        { label: 'Details', content: <DetailsTab data={data} /> },
        {
          label: 'Issues',
          count: issues.length,
          content: <IssuesTab data={data} />,
        },
      ]} />
    </div>
  );
}
