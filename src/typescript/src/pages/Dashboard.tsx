import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { listWorkflows, deleteWorkflow } from '../api/workflows';
import type { WorkflowSummary } from '../types/api';

const PHASE_LABELS: Record<string, string> = {
  documentation: 'Documentation',
  coding: 'Coding',
  compliance: 'Compliance',
  prior_auth: 'Prior Auth',
  quality_assurance: 'QA',
};

export default function Dashboard() {
  const navigate = useNavigate();
  const [workflows, setWorkflows] = useState<WorkflowSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [deleting, setDeleting] = useState(false);

  const fetchWorkflows = async () => {
    try {
      const data = await listWorkflows();
      setWorkflows(data);
    } catch (err) {
      console.error('Failed to fetch workflows', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchWorkflows();
  }, []);

  const toggleSelect = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleSelectAll = () => {
    if (selectedIds.size === workflows.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(workflows.map((w) => w.id)));
    }
  };

  const handleBulkDelete = async () => {
    if (!confirm(`Delete ${selectedIds.size} workflow(s)?`)) return;
    setDeleting(true);
    try {
      await Promise.all([...selectedIds].map((id) => deleteWorkflow(id)));
      setWorkflows((prev) => prev.filter((w) => !selectedIds.has(w.id)));
      setSelectedIds(new Set());
    } catch (err) {
      console.error('Failed to delete workflows', err);
    } finally {
      setDeleting(false);
    }
  };

  if (loading) {
    return <div className="loading">Loading workflows...</div>;
  }

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <h1>Workflows</h1>
        <div className="dashboard-actions">
          {selectedIds.size > 0 && (
            <button
              className="btn-danger"
              onClick={handleBulkDelete}
              disabled={deleting}
            >
              {deleting ? 'Deleting...' : `Delete (${selectedIds.size})`}
            </button>
          )}
          <button className="btn-primary" onClick={() => navigate('/workflows/new')}>
            + New Workflow
          </button>
        </div>
      </header>

      {workflows.length === 0 ? (
        <div className="empty-state">
          <p>No workflows yet. Create one to get started.</p>
        </div>
      ) : (
        <div className="wf-grid">
          {/* Header row */}
          <div className="wf-grid-header">
            <div className="wf-grid-cell wf-cell-check">
              <input
                type="checkbox"
                checked={selectedIds.size === workflows.length}
                onChange={toggleSelectAll}
              />
            </div>
            <div className="wf-grid-cell wf-cell-id">ID</div>
            <div className="wf-grid-cell wf-cell-phase">Phase</div>
            <div className="wf-grid-cell wf-cell-status">Status</div>
            <div className="wf-grid-cell wf-cell-date">Date</div>
            <div className="wf-grid-cell wf-cell-tokens">Tokens</div>
          </div>

          {/* Data rows */}
          {workflows.map((w) => {
            const totalTokens = w.total_input_tokens + w.total_output_tokens;
            const phaseLabel = w.current_phase
              ? PHASE_LABELS[w.current_phase] || w.current_phase
              : '—';

            return (
              <div
                key={w.id}
                className={`wf-grid-row ${selectedIds.has(w.id) ? 'wf-grid-row--selected' : ''}`}
                onClick={() => navigate(`/workflows/${w.id}`)}
              >
                <div className="wf-grid-cell wf-cell-check" onClick={(e) => toggleSelect(w.id, e)}>
                  <input
                    type="checkbox"
                    checked={selectedIds.has(w.id)}
                    readOnly
                  />
                </div>
                <div className="wf-grid-cell wf-cell-id">
                  <span className="wf-id-text">#{w.id.slice(0, 8)}</span>
                </div>
                <div className="wf-grid-cell wf-cell-phase">{phaseLabel}</div>
                <div className="wf-grid-cell wf-cell-status">
                  <span className={`status-badge status-${w.status}`}>
                    {w.status.replace('_', ' ')}
                  </span>
                </div>
                <div className="wf-grid-cell wf-cell-date">
                  {new Date(w.created_at).toLocaleDateString()}
                </div>
                <div className="wf-grid-cell wf-cell-tokens">
                  {totalTokens > 0 ? totalTokens.toLocaleString() : '—'}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
