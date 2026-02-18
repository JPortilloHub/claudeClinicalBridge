/* eslint-disable @typescript-eslint/no-explicit-any */

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

export default function ComplianceView({ data }: Props) {
  const status = data?.overall_status;
  const risk = data?.risk_level;
  const score = data?.audit_readiness_score;
  const codeVals = data?.code_validations || [];
  const emVal = data?.em_validation;
  const issues = data?.compliance_issues || [];
  const payer = data?.payer_checks;

  // Sort issues: critical first
  const sortedIssues = [...issues].sort((a: any, b: any) => {
    const order: Record<string, number> = { critical: 0, warning: 1, info: 2 };
    return (order[a.severity] ?? 3) - (order[b.severity] ?? 3);
  });

  return (
    <div className="renderer-container">
      {/* STATUS BANNER */}
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

      {/* AUDIT READINESS */}
      {score != null && (
        <div className="r-section">
          <h4 className="r-section-title">Audit Readiness</h4>
          <ProgressBar value={score} />
        </div>
      )}

      {/* CODE VALIDATIONS */}
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

      {/* E/M VALIDATION */}
      {emVal && (
        <div className="r-section">
          <h4 className="r-section-title">E/M Validation</h4>
          <div className="r-em-validation">
            <div className="r-em-compare">
              <div className="r-em-compare-item">
                <span className="r-label">Documented</span>
                <span className="r-code-value r-code-value-sm">{emVal.documented_level || '—'}</span>
              </div>
              <span className="r-em-arrow">{'\u2192'}</span>
              <div className="r-em-compare-item">
                <span className="r-label">Supported</span>
                <span className="r-code-value r-code-value-sm">{emVal.supported_level || '—'}</span>
              </div>
              <span className={`r-badge ${emVal.status === 'pass' ? 'r-badge-green' : 'r-badge-red'}`}>
                {emVal.status || '—'}
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

      {/* COMPLIANCE ISSUES */}
      {sortedIssues.length > 0 && (
        <div className="r-section">
          <h4 className="r-section-title">Compliance Issues ({sortedIssues.length})</h4>
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
      )}

      {sortedIssues.length === 0 && (
        <div className="r-empty-success">No compliance issues found</div>
      )}

      {/* PAYER CHECKS */}
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
