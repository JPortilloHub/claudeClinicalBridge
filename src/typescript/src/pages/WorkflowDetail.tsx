import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { getWorkflow, runPhase, approvePhase } from '../api/workflows';
import type { WorkflowDetail as WorkflowType } from '../types/api';
import ClinicalNotePane from '../components/ClinicalNotePane';
import PhaseStepper from '../components/PhaseStepper';
import PhaseContentPanel from '../components/PhaseContentPanel';

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

  const [activePhase, setActivePhase] = useState<string>(PHASE_ORDER[0]);
  const [noteCollapsed, setNoteCollapsed] = useState(false);
  const userSelectedPhase = useRef(false);

  const fetchWorkflow = useCallback(async () => {
    if (!id) return;
    try {
      const data = await getWorkflow(id);
      setWorkflow(data);
      setError('');

      if (!userSelectedPhase.current && data.current_phase) {
        setActivePhase(data.current_phase);
      }

      const hasRunning = data.phase_results.some((p) => p.status === 'running');
      isPolling.current = hasRunning;
    } catch {
      setError('Failed to load workflow');
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchWorkflow();
  }, [fetchWorkflow]);

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
      userSelectedPhase.current = false;
      await fetchWorkflow();
    } catch {
      setError(`Failed to approve phase: ${phaseName}`);
    }
  };

  const handleSelectPhase = (name: string) => {
    userSelectedPhase.current = true;
    setActivePhase(name);
  };

  // Filter out prior_auth when skipped (Req 1)
  const visiblePhases = useMemo(() => {
    if (!workflow) return PHASE_ORDER;
    return workflow.skip_prior_auth
      ? PHASE_ORDER.filter((p) => p !== 'prior_auth')
      : PHASE_ORDER;
  }, [workflow]);

  if (loading) return <div className="loading">Loading workflow...</div>;
  if (error && !workflow) return <div className="error-message">{error}</div>;
  if (!workflow) return <div className="error-message">Workflow not found</div>;

  const phaseMap = Object.fromEntries(
    workflow.phase_results.map((p) => [p.phase_name, p])
  );

  const steps = visiblePhases.map((name) => ({
    name,
    label: PHASE_LABELS[name],
    status: phaseMap[name]?.status || 'pending',
  }));

  const currentPhaseResult = phaseMap[activePhase];
  const shortId = id ? id.slice(0, 8) : '';

  return (
    <div className="wd-container">
      <ClinicalNotePane
        workflow={workflow}
        collapsed={noteCollapsed}
        onToggleCollapse={() => setNoteCollapsed(!noteCollapsed)}
      />

      <div className="wd-content-pane">
        {/* Header bar */}
        <div className="wd-header">
          <div className="wd-header-left">
            <Link to="/" className="wd-back-btn">&larr; Back</Link>
            <h2 className="wd-title">Workflow <span className="wd-title-id">#{shortId}</span></h2>
            <span className={`status-badge status-${workflow.status}`}>
              {workflow.status.replace('_', ' ')}
            </span>
          </div>
        </div>

        {error && <div className="error-message" style={{ margin: '0 24px', marginTop: '12px' }}>{error}</div>}

        <PhaseStepper
          phases={steps}
          activePhase={activePhase}
          onSelectPhase={handleSelectPhase}
        />

        {currentPhaseResult ? (
          <PhaseContentPanel
            key={activePhase}
            phase={currentPhaseResult}
            label={PHASE_LABELS[activePhase]}
            workflowId={id!}
            isCurrentPhase={workflow.current_phase === activePhase}
            onRun={() => handleRunPhase(activePhase)}
            onApprove={() => handleApprovePhase(activePhase)}
            onContentUpdated={fetchWorkflow}
          />
        ) : (
          <div className="wd-phase-content-scroll">
            <div className="empty-state">Phase not available</div>
          </div>
        )}
      </div>
    </div>
  );
}
