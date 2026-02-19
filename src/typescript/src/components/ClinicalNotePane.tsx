import type { WorkflowDetail } from '../types/api';

interface Props {
  workflow: WorkflowDetail;
  collapsed: boolean;
  onToggleCollapse: () => void;
}

export default function ClinicalNotePane({ workflow, collapsed, onToggleCollapse }: Props) {
  if (collapsed) {
    return (
      <div className="wd-note-pane wd-note-pane--collapsed" onClick={onToggleCollapse}>
        <div className="wd-note-collapsed-label">Clinical Note</div>
      </div>
    );
  }

  return (
    <div className="wd-note-pane">
      <div className="wd-note-pane-header">
        <h3>Clinical Note</h3>
        <button className="wd-note-collapse-btn" onClick={onToggleCollapse}>
          &#9664; Collapse
        </button>
      </div>
      <div className="wd-note-pane-body">
        <pre className="wd-note-text">{workflow.raw_note}</pre>
        <div className="wd-note-meta">
          {workflow.patient_id && (
            <div className="wd-note-meta-item">
              <span className="wd-note-meta-label">Patient</span>
              <span className="wd-note-meta-value">{workflow.patient_id}</span>
            </div>
          )}
          {workflow.payer && (
            <div className="wd-note-meta-item">
              <span className="wd-note-meta-label">Payer</span>
              <span className="wd-note-meta-value">{workflow.payer}</span>
            </div>
          )}
          {workflow.procedure && (
            <div className="wd-note-meta-item">
              <span className="wd-note-meta-label">Procedure</span>
              <span className="wd-note-meta-value">{workflow.procedure}</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
