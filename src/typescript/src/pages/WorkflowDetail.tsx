import { useCallback, useEffect, useRef, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { getWorkflow, runPhase, approvePhase } from '../api/workflows';
import type { WorkflowDetail as WorkflowType } from '../types/api';
import PhaseCard from '../components/PhaseCard';

const PHASE_ORDER = ['documentation', 'coding', 'compliance', 'prior_auth', 'quality_assurance'];
const PHASE_LABELS: Record<string, string> = {
  documentation: 'Clinical Documentation',
  coding: 'Medical Coding',
  compliance: 'Compliance Validation',
  prior_auth: 'Prior Authorization',
  quality_assurance: 'Quality Assurance',
};

export default function WorkflowDetail() {
  const { id } = useParams<{ id: string }>();
  const [workflow, setWorkflow] = useState<WorkflowType | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const isPolling = useRef(false);

  const fetchWorkflow = useCallback(async () => {
    if (!id) return;
    try {
      const data = await getWorkflow(id);
      setWorkflow(data);
      setError('');

      // Start or stop polling based on whether any phase is running
      const hasRunning = data.phase_results.some((p) => p.status === 'running');
      isPolling.current = hasRunning;
    } catch {
      setError('Failed to load workflow');
    } finally {
      setLoading(false);
    }
  }, [id]);

  // Initial fetch
  useEffect(() => {
    fetchWorkflow();
  }, [fetchWorkflow]);

  // Polling interval — always runs but only fetches when isPolling is true
  useEffect(() => {
    const interval = setInterval(() => {
      if (isPolling.current) {
        fetchWorkflow();
      }
    }, 3000);

    return () => clearInterval(interval);
  }, [fetchWorkflow]);

  const handleRunPhase = async (phaseName: string) => {
    if (!id) return;
    try {
      await runPhase(id, phaseName);
      isPolling.current = true;
      setTimeout(fetchWorkflow, 1000);
    } catch {
      setError(`Failed to start phase: ${phaseName}`);
    }
  };

  const handleApprovePhase = async (phaseName: string) => {
    if (!id) return;
    try {
      await approvePhase(id, phaseName);
      await fetchWorkflow();
    } catch {
      setError(`Failed to approve phase: ${phaseName}`);
    }
  };

  if (loading) return <div className="loading">Loading workflow...</div>;
  if (error && !workflow) return <div className="error-message">{error}</div>;
  if (!workflow) return <div className="error-message">Workflow not found</div>;

  const phaseMap = Object.fromEntries(
    workflow.phase_results.map((p) => [p.phase_name, p])
  );

  return (
    <div className="workflow-detail">
      <header className="workflow-detail-header">
        <Link to="/" className="back-link">&larr; Back to Workflows</Link>
        <div className="workflow-title">
          <h1>Workflow</h1>
          <span className={`status-badge status-${workflow.status}`}>
            {workflow.status.replace('_', ' ')}
          </span>
        </div>
        {workflow.total_input_tokens + workflow.total_output_tokens > 0 && (
          <div className="workflow-stats">
            Tokens: {(workflow.total_input_tokens + workflow.total_output_tokens).toLocaleString()}
          </div>
        )}
      </header>

      {error && <div className="error-message">{error}</div>}

      <section className="raw-note-section">
        <h2>Clinical Note</h2>
        <pre className="raw-note">{workflow.raw_note}</pre>
        <div className="note-meta">
          {workflow.patient_id && <span>Patient: {workflow.patient_id}</span>}
          {workflow.payer && <span>Payer: {workflow.payer}</span>}
          {workflow.procedure && <span>Procedure: {workflow.procedure}</span>}
        </div>
      </section>

      <section className="phases-section">
        <h2>Pipeline Phases</h2>
        <div className="phase-list">
          {PHASE_ORDER.map((phaseName) => {
            const phase = phaseMap[phaseName];
            if (!phase) return null;

            return (
              <PhaseCard
                key={phaseName}
                phase={phase}
                label={PHASE_LABELS[phaseName]}
                workflowId={id!}
                isCurrentPhase={workflow.current_phase === phaseName}
                onRun={() => handleRunPhase(phaseName)}
                onApprove={() => handleApprovePhase(phaseName)}
                onContentUpdated={fetchWorkflow}
              />
            );
          })}
        </div>
      </section>
    </div>
  );
}
