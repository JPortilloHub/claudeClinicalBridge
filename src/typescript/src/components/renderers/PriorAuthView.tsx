/* eslint-disable @typescript-eslint/no-explicit-any */
import Tabs from './Tabs';

interface Props { data: any; }

function likelihoodColor(l: string | undefined): string {
  if (!l) return '';
  const v = l.toLowerCase();
  if (v === 'high') return 'r-likelihood-high';
  if (v === 'moderate') return 'r-likelihood-moderate';
  return 'r-likelihood-low';
}

/* ── Overview tab ─────────────────────────────────────────────── */
function OverviewTab({ data }: Props) {
  const proc = data?.procedure;
  const required = data?.prior_auth_required;
  const likelihood = data?.approval_likelihood;
  const rationale = data?.approval_likelihood_rationale;
  const met = data?.criteria_assessment?.criteria_met || [];
  const notMet = data?.criteria_assessment?.criteria_not_met || [];

  return (
    <div className="r-tab-inner">
      {/* Procedure header */}
      {proc && (
        <div className="r-section">
          <div className="r-proc-header">
            {proc.cpt_code && <span className="r-code-value">{proc.cpt_code}</span>}
            <div>
              <strong>{proc.description || 'Procedure'}</strong>
              {proc.payer && <span className="r-payer-label">Payer: {proc.payer}</span>}
            </div>
          </div>
        </div>
      )}

      {/* Auth required indicator */}
      <div className={`r-auth-required ${required ? 'r-auth-yes' : 'r-auth-no'}`}>
        <span className="r-auth-icon">{required ? '!' : '\u2713'}</span>
        <span>Prior Authorization {required ? 'Required' : 'Not Required'}</span>
      </div>

      {/* Approval likelihood */}
      {likelihood && (
        <div className="r-section">
          <h4 className="r-section-title">Approval Likelihood</h4>
          <div className={`r-likelihood ${likelihoodColor(likelihood)}`}>
            <span className="r-likelihood-value">{likelihood}</span>
          </div>
          {rationale && <p className="r-card-detail">{rationale}</p>}
        </div>
      )}

      {/* Criteria summary */}
      {(met.length > 0 || notMet.length > 0) && (
        <div className="r-section">
          <h4 className="r-section-title">Criteria Summary</h4>
          <div className="r-criteria-summary">
            <div className="r-criteria-count r-criteria-count-met">
              <span className="r-criteria-num">{met.length}</span>
              <span>Met</span>
            </div>
            <div className="r-criteria-count r-criteria-count-notmet">
              <span className="r-criteria-num">{notMet.length}</span>
              <span>Not Met</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

/* ── Details tab ──────────────────────────────────────────────── */
function DetailsTab({ data }: Props) {
  const met = data?.criteria_assessment?.criteria_met || [];
  const notMet = data?.criteria_assessment?.criteria_not_met || [];
  const checklist = data?.documentation_checklist;
  const summary = data?.medical_necessity_summary;

  return (
    <div className="r-tab-inner">
      {/* Criteria assessment */}
      {(met.length > 0 || notMet.length > 0) && (
        <div className="r-section">
          <h4 className="r-section-title">Criteria Assessment</h4>

          {met.length > 0 && (
            <div className="r-criteria-group">
              <h5 className="r-sub-label r-sub-label-green">Criteria Met</h5>
              {met.map((c: any, i: number) => (
                <div key={i} className="r-criteria-item r-criteria-met">
                  <span className="r-icon-pass">{'\u2713'}</span>
                  <div>
                    <strong>{c.criterion}</strong>
                    {c.supporting_evidence && <p className="r-card-note">{c.supporting_evidence}</p>}
                  </div>
                </div>
              ))}
            </div>
          )}

          {notMet.length > 0 && (
            <div className="r-criteria-group">
              <h5 className="r-sub-label r-sub-label-red">Criteria Not Met</h5>
              {notMet.map((c: any, i: number) => (
                <div key={i} className="r-criteria-item r-criteria-not-met">
                  <span className="r-icon-fail">{'\u2717'}</span>
                  <div>
                    <strong>{c.criterion}</strong>
                    {c.status && <span className="r-badge r-badge-yellow">{c.status.replace(/_/g, ' ')}</span>}
                    {c.supporting_evidence && <p className="r-card-note">{c.supporting_evidence}</p>}
                    {c.action_needed && <p className="r-card-remediation"><strong>Action:</strong> {c.action_needed}</p>}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Documentation checklist */}
      {checklist && (
        <div className="r-section">
          <h4 className="r-section-title">Documentation Checklist</h4>
          <div className="r-checklist">
            {(checklist.complete || []).map((item: string, i: number) => (
              <div key={`c-${i}`} className="r-checklist-item">
                <span className="r-icon-pass">{'\u2713'}</span>
                <span>{item}</span>
              </div>
            ))}
            {(checklist.partial || []).map((item: string, i: number) => (
              <div key={`p-${i}`} className="r-checklist-item">
                <span className="r-icon-warn">~</span>
                <span>{item}</span>
              </div>
            ))}
            {(checklist.missing || []).map((item: string, i: number) => (
              <div key={`m-${i}`} className="r-checklist-item">
                <span className="r-icon-fail">{'\u2717'}</span>
                <span>{item}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Medical necessity */}
      {summary && (
        <div className="r-section">
          <h4 className="r-section-title">Medical Necessity Summary</h4>
          <p className="r-text-block">{summary}</p>
        </div>
      )}
    </div>
  );
}

/* ── Issues tab ───────────────────────────────────────────────── */
function IssuesTab({ data }: Props) {
  const actions = data?.recommended_actions || [];
  const appeal = data?.appeal_considerations || [];
  const notMet = data?.criteria_assessment?.criteria_not_met || [];

  if (actions.length === 0 && appeal.length === 0 && notMet.length === 0) {
    return (
      <div className="r-tab-inner">
        <div className="r-empty-success">No actions needed</div>
      </div>
    );
  }

  return (
    <div className="r-tab-inner">
      {actions.length > 0 && (
        <div className="r-alert r-alert-info">
          <h5>Recommended Actions</h5>
          <ol className="r-list r-list-numbered">
            {actions.map((a: string, i: number) => <li key={i}>{a}</li>)}
          </ol>
        </div>
      )}

      {appeal.length > 0 && (
        <div className="r-section">
          <h4 className="r-section-title">Appeal Considerations</h4>
          <ul className="r-list">
            {appeal.map((a: string, i: number) => <li key={i}>{a}</li>)}
          </ul>
        </div>
      )}
    </div>
  );
}

/* ── Main component ───────────────────────────────────────────── */
export default function PriorAuthView({ data }: Props) {
  if (!data) return null;

  const actions = data?.recommended_actions || [];
  const notMet = data?.criteria_assessment?.criteria_not_met || [];
  const issueCount = actions.length + notMet.length;

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
