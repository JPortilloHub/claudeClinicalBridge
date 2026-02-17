import { useState } from 'react';
import type { PhaseResult } from '../types/api';
import PhaseEditor from './PhaseEditor';

interface PhaseCardProps {
  phase: PhaseResult;
  label: string;
  workflowId: string;
  isCurrentPhase: boolean;
  onRun: () => void;
  onApprove: () => void;
  onContentUpdated: () => void;
}

function formatContent(raw: string | null): string {
  if (!raw) return '';
  try {
    return JSON.stringify(JSON.parse(raw), null, 2);
  } catch {
    return raw;
  }
}

export default function PhaseCard({
  phase,
  label,
  workflowId,
  isCurrentPhase,
  onRun,
  onApprove,
  onContentUpdated,
}: PhaseCardProps) {
  const [editing, setEditing] = useState(false);
  const [expanded, setExpanded] = useState(isCurrentPhase);

  const canRun = phase.status === 'pending' && isCurrentPhase;
  const canApprove = phase.status === 'completed' && isCurrentPhase;
  const isRunning = phase.status === 'running';
  const displayContent = phase.edited_content || phase.content;

  return (
    <div className={`phase-card phase-${phase.status} ${isCurrentPhase ? 'phase-current' : ''}`}>
      <div className="phase-card-header" onClick={() => setExpanded(!expanded)}>
        <div className="phase-title">
          <span className={`phase-indicator phase-indicator-${phase.status}`} />
          <h3>{label}</h3>
          <span className={`phase-status-badge phase-status-${phase.status}`}>
            {phase.status}
          </span>
        </div>
        <div className="phase-meta">
          {phase.duration_seconds && (
            <span className="meta-item">{phase.duration_seconds.toFixed(1)}s</span>
          )}
          {phase.input_tokens && phase.output_tokens && (
            <span className="meta-item">
              {(phase.input_tokens + phase.output_tokens).toLocaleString()} tokens
            </span>
          )}
          <span className="expand-icon">{expanded ? '\u25BC' : '\u25B6'}</span>
        </div>
      </div>

      {expanded && (
        <div className="phase-card-body">
          {phase.error && (
            <div className="phase-error">
              <strong>Error:</strong> {phase.error}
            </div>
          )}

          {isRunning && (
            <div className="phase-running">
              <div className="spinner" />
              <span>Running agent... this takes 60-90 seconds</span>
            </div>
          )}

          {displayContent && !editing && (
            <pre className="phase-content">{formatContent(displayContent)}</pre>
          )}

          {editing && (
            <PhaseEditor
              workflowId={workflowId}
              phaseName={phase.phase_name}
              initialContent={displayContent || ''}
              onSave={() => {
                setEditing(false);
                onContentUpdated();
              }}
              onCancel={() => setEditing(false)}
            />
          )}

          {phase.edited_content && !editing && (
            <div className="edited-badge">Edited by reviewer</div>
          )}

          <div className="phase-actions">
            {canRun && (
              <button className="btn-primary" onClick={onRun}>
                Run Phase
              </button>
            )}
            {canApprove && !editing && (
              <>
                <button className="btn-secondary" onClick={() => setEditing(true)}>
                  Edit Output
                </button>
                <button className="btn-primary" onClick={onApprove}>
                  Approve &amp; Continue
                </button>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
