import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { listWorkflows, deleteWorkflow } from '../api/workflows';
import type { WorkflowSummary } from '../types/api';

const STATUS_COLORS: Record<string, string> = {
  pending: '#6b7280',
  in_progress: '#3b82f6',
  needs_review: '#f59e0b',
  completed: '#10b981',
  failed: '#ef4444',
};

export default function Dashboard() {
  const navigate = useNavigate();
  const [workflows, setWorkflows] = useState<WorkflowSummary[]>([]);
  const [loading, setLoading] = useState(true);

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

  const handleDelete = async (id: string, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (!confirm('Delete this workflow?')) return;
    await deleteWorkflow(id);
    setWorkflows((prev) => prev.filter((w) => w.id !== id));
  };

  if (loading) {
    return <div className="loading">Loading workflows...</div>;
  }

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <h1>Workflows</h1>
        <button className="btn-primary" onClick={() => navigate('/workflows/new')}>
          + New Workflow
        </button>
      </header>

      {workflows.length === 0 ? (
        <div className="empty-state">
          <p>No workflows yet. Create one to get started.</p>
        </div>
      ) : (
        <div className="workflow-list">
          {workflows.map((w) => (
            <Link to={`/workflows/${w.id}`} key={w.id} className="workflow-card">
              <div className="workflow-card-header">
                <span
                  className="status-badge"
                  style={{ backgroundColor: STATUS_COLORS[w.status] || '#6b7280' }}
                >
                  {w.status.replace('_', ' ')}
                </span>
                <span className="workflow-date">
                  {new Date(w.created_at).toLocaleDateString()}
                </span>
              </div>
              <p className="workflow-note">
                {w.raw_note.length > 120 ? w.raw_note.slice(0, 120) + '...' : w.raw_note}
              </p>
              <div className="workflow-meta">
                {w.current_phase && w.current_phase !== 'done' && (
                  <span>Phase: {w.current_phase}</span>
                )}
                {w.payer && <span>Payer: {w.payer}</span>}
                {w.total_input_tokens + w.total_output_tokens > 0 && (
                  <span>Tokens: {w.total_input_tokens + w.total_output_tokens}</span>
                )}
                <button
                  className="btn-delete"
                  onClick={(e) => handleDelete(w.id, e)}
                  title="Delete workflow"
                >
                  Delete
                </button>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
