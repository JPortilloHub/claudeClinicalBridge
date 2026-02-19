import { useState } from 'react';
import type { PhaseResult } from '../types/api';
import PhaseEditor from './PhaseEditor';
import ContentRenderer from './renderers/ContentRenderer';

interface Props {
  phase: PhaseResult;
  label: string;
  workflowId: string;
  isCurrentPhase: boolean;
  showTechnicalInfo: boolean;
  onRun: () => void;
  onApprove: () => void;
  onContentUpdated: () => void;
}

export default function PhaseContentPanel({
  phase,
  label,
  workflowId,
  isCurrentPhase,
  showTechnicalInfo,
  onRun,
  onApprove,
  onContentUpdated,
}: Props) {
  const [editing, setEditing] = useState(false);
  const [showRaw, setShowRaw] = useState(false);

  const canRun = phase.status === 'pending' && isCurrentPhase;
  const canApprove = phase.status === 'completed' && isCurrentPhase;
  const isRunning = phase.status === 'running';
  const isFailed = phase.status === 'failed';
  const displayContent = phase.edited_content || phase.content;

  return (
    <div className="wd-phase-content-scroll">
      {/* Technical info bar */}
      {showTechnicalInfo && (phase.duration_seconds || (phase.input_tokens && phase.output_tokens)) && (
        <div className="wd-phase-technical-bar">
          {phase.duration_seconds && (
            <span>Duration: {phase.duration_seconds.toFixed(1)}s</span>
          )}
          {phase.input_tokens && phase.output_tokens && (
            <span>Tokens: {(phase.input_tokens + phase.output_tokens).toLocaleString()}</span>
          )}
        </div>
      )}

      {/* Error banner */}
      {isFailed && phase.error && (
        <div className="phase-error-banner">
          <div className="phase-error-icon">!</div>
          <div className="phase-error-content">
            <strong>Phase Failed</strong>
            <p>{phase.error}</p>
          </div>
          {isCurrentPhase && (
            <button className="btn-secondary btn-sm" onClick={onRun}>
              Retry
            </button>
          )}
        </div>
      )}

      {/* Running skeleton */}
      {isRunning && (
        <div className="phase-running-skeleton">
          <div className="phase-running-header">
            <div className="spinner" />
            <span>Running {label}... this takes 60-90 seconds</span>
          </div>
          <div className="skeleton-kpi-row">
            <div className="skeleton-kpi" />
            <div className="skeleton-kpi" />
            <div className="skeleton-kpi" />
          </div>
          <div className="skeleton-block" />
          <div className="skeleton-block skeleton-block-sm" />
        </div>
      )}

      {/* Content display */}
      {displayContent && !editing && !isRunning && (
        <>
          {showRaw ? (
            <pre className="phase-content">{displayContent}</pre>
          ) : (
            <ContentRenderer phaseName={phase.phase_name} content={displayContent} />
          )}
          <button
            className="btn-toggle-raw"
            onClick={() => setShowRaw(!showRaw)}
          >
            {showRaw ? 'Formatted View' : 'View Technical Data'}
          </button>
        </>
      )}

      {/* Pending state */}
      {phase.status === 'pending' && !displayContent && (
        <div className="empty-state" style={{ padding: '40px 0' }}>
          This phase has not been run yet.
        </div>
      )}

      {/* Editor */}
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

      {/* Actions */}
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
  );
}
