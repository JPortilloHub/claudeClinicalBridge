/* eslint-disable @typescript-eslint/no-explicit-any */
import Tabs from './Tabs';

interface Props { data: any; }

function KeyValueGrid({ obj }: { obj: any }) {
  if (!obj || typeof obj !== 'object') return null;
  const entries = Object.entries(obj).filter(([, v]) => v != null && v !== '');
  if (entries.length === 0) return null;
  return (
    <div className="r-kv-grid">
      {entries.map(([k, v]) => (
        <div key={k} className="r-kv-row">
          <span className="r-kv-key">{k.replace(/_/g, ' ')}</span>
          <span className="r-kv-value">{typeof v === 'object' ? JSON.stringify(v) : String(v)}</span>
        </div>
      ))}
    </div>
  );
}

function BulletList({ items, icon }: { items: any[]; icon?: string }) {
  if (!items || items.length === 0) return null;
  return (
    <ul className="r-list">
      {items.map((item, i) => (
        <li key={i}>{icon && <span className="r-list-icon">{icon}</span>}{typeof item === 'object' ? JSON.stringify(item) : String(item)}</li>
      ))}
    </ul>
  );
}

function SectionLabel({ text }: { text: string }) {
  return <h5 className="r-sub-label">{text}</h5>;
}

/* ── Overview tab ─────────────────────────────────────────────── */
function OverviewTab({ data }: Props) {
  const subj = data?.subjective;
  const assess = data?.assessment;
  const plan = data?.plan;

  return (
    <div className="r-tab-inner">
      {/* Chief complaint summary card */}
      {subj?.chief_complaint && (
        <div className="r-highlight-box">
          <span className="r-label">Chief Complaint</span>
          <p className="r-value-lg">{subj.chief_complaint}</p>
        </div>
      )}

      {/* Completeness overview */}
      <div className="r-overview-grid">
        <div className="r-overview-item">
          <span className="r-overview-icon r-soap-s-icon">S</span>
          <span className="r-overview-label">Subjective</span>
          <span className={`r-badge ${subj ? 'r-badge-green' : 'r-badge-gray'}`}>
            {subj ? 'Complete' : 'Missing'}
          </span>
        </div>
        <div className="r-overview-item">
          <span className="r-overview-icon r-soap-o-icon">O</span>
          <span className="r-overview-label">Objective</span>
          <span className={`r-badge ${data?.objective ? 'r-badge-green' : 'r-badge-gray'}`}>
            {data?.objective ? 'Complete' : 'Missing'}
          </span>
        </div>
        <div className="r-overview-item">
          <span className="r-overview-icon r-soap-a-icon">A</span>
          <span className="r-overview-label">Assessment</span>
          <span className={`r-badge ${assess?.length ? 'r-badge-green' : 'r-badge-gray'}`}>
            {assess?.length ? `${assess.length} diagnoses` : 'Missing'}
          </span>
        </div>
        <div className="r-overview-item">
          <span className="r-overview-icon r-soap-p-icon">P</span>
          <span className="r-overview-label">Plan</span>
          <span className={`r-badge ${plan?.length ? 'r-badge-green' : 'r-badge-gray'}`}>
            {plan?.length ? `${plan.length} items` : 'Missing'}
          </span>
        </div>
      </div>

      {/* Assessment summary cards */}
      {Array.isArray(assess) && assess.length > 0 && (
        <div className="r-section">
          <h4 className="r-section-title">Assessment Summary</h4>
          {assess.map((dx: any, i: number) => (
            <div key={i} className="r-card">
              <div className="r-card-header">
                {dx.icd10_hint && <span className="r-badge r-badge-blue">{dx.icd10_hint}</span>}
                <strong>{dx.diagnosis || `Diagnosis ${i + 1}`}</strong>
              </div>
              {dx.clinical_reasoning && (
                <p className="r-card-detail">{dx.clinical_reasoning}</p>
              )}
            </div>
          ))}
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
        <div className="r-section r-soap-s">
          <h4 className="r-section-title">Subjective</h4>

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
              <BulletList items={subj.pmh} />
            </>
          )}

          <div className="r-inline-lists">
            {subj.medications && subj.medications.length > 0 && (
              <div className="r-inline-list-item">
                <SectionLabel text="Medications" />
                <BulletList items={subj.medications} />
              </div>
            )}
            {subj.allergies && subj.allergies.length > 0 && (
              <div className="r-inline-list-item">
                <SectionLabel text="Allergies" />
                <BulletList items={subj.allergies} />
              </div>
            )}
          </div>
        </div>
      )}

      {/* OBJECTIVE */}
      {obj && (
        <div className="r-section r-soap-o">
          <h4 className="r-section-title">Objective</h4>

          {obj.vitals && typeof obj.vitals === 'object' && (
            <>
              <SectionLabel text="Vital Signs" />
              <div className="r-vitals-grid">
                {Object.entries(obj.vitals).filter(([, v]) => v != null && v !== '').map(([k, v]) => (
                  <div key={k} className="r-vital-item">
                    <span className="r-vital-label">{k.replace(/_/g, ' ')}</span>
                    <span className="r-vital-value">{String(v)}</span>
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
        </div>
      )}

      {/* ASSESSMENT */}
      {assess && Array.isArray(assess) && assess.length > 0 && (
        <div className="r-section r-soap-a">
          <h4 className="r-section-title">Assessment</h4>
          {assess.map((dx: any, i: number) => (
            <div key={i} className="r-card">
              <div className="r-card-header">
                {dx.icd10_hint && <span className="r-badge r-badge-blue">{dx.icd10_hint}</span>}
                <strong>{dx.diagnosis || `Diagnosis ${i + 1}`}</strong>
              </div>
              {dx.clinical_reasoning && (
                <p className="r-card-detail">{dx.clinical_reasoning}</p>
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
            </div>
          ))}
        </div>
      )}

      {/* PLAN */}
      {plan && Array.isArray(plan) && plan.length > 0 && (
        <div className="r-section r-soap-p">
          <h4 className="r-section-title">Plan</h4>
          {plan.map((item: any, i: number) => (
            <div key={i} className="r-card">
              <div className="r-card-header">
                <strong>{item.diagnosis || `Plan ${i + 1}`}</strong>
              </div>
              {item.actions && <BulletList items={item.actions} />}
            </div>
          ))}
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
        <div className="r-alert r-alert-warning">
          <h5>Documentation Gaps</h5>
          <BulletList items={gaps} icon="!" />
        </div>
      )}
      {hints && (
        <div className="r-alert r-alert-info">
          <h5>Coding Hints</h5>
          <KeyValueGrid obj={hints} />
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
