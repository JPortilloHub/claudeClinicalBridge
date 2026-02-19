import { useCallback, useEffect, useRef, useState } from 'react';
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

  // UI state for the new layout
  const [activePhase, setActivePhase] = useState<string>(PHASE_ORDER[0]);
  const [noteCollapsed, setNoteCollapsed] = useState(false);
  const [showTechnicalInfo, setShowTechnicalInfo] = useState(false);
  const userSelectedPhase = useRef(false);

  const fetchWorkflow = useCallback(async () => {
    if (!id) return;
    try {
      const data = await getWorkflow(id);
      setWorkflow(data);
      setError('');

      // Auto-advance to current phase unless user manually selected one
      if (!userSelectedPhase.current && data.current_phase) {
        setActivePhase(data.current_phase);
      }

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
      userSelectedPhase.current = false; // allow auto-advance after approve
      await fetchWorkflow();
    } catch {
      setError(`Failed to approve phase: ${phaseName}`);
    }
  };

  const handleSelectPhase = (name: string) => {
    userSelectedPhase.current = true;
    setActivePhase(name);
  };

  if (loading) return <div className="loading">Loading workflow...</div>;
  if (error && !workflow) return <div className="error-message">{error}</div>;
  if (!workflow) return <div className="error-message">Workflow not found</div>;

  const phaseMap = Object.fromEntries(
    workflow.phase_results.map((p) => [p.phase_name, p])
  );

  const steps = PHASE_ORDER.map((name) => ({
    name,
    label: PHASE_LABELS[name],
    status: phaseMap[name]?.status || 'pending',
  }));

  const currentPhaseResult = phaseMap[activePhase];

  return (
    <div className="wd-container">
      {/* Left pane: clinical note */}
      <ClinicalNotePane
        workflow={workflow}
        collapsed={noteCollapsed}
        onToggleCollapse={() => setNoteCollapsed(!noteCollapsed)}
      />

      {/* Right pane: header + stepper + phase content */}
      <div className="wd-content-pane">
        {/* Header bar */}
        <div className="wd-header">
          <div className="wd-header-left">
            <Link to="/" className="back-link">&larr; Back</Link>
            <h2>Workflow</h2>
            <span className={`status-badge status-${workflow.status}`}>
              {workflow.status.replace('_', ' ')}
            </span>
          </div>
          <div className="wd-header-right">
            <button
              className={`btn-toggle-technical ${showTechnicalInfo ? 'btn-toggle-technical--active' : ''}`}
              onClick={() => setShowTechnicalInfo(!showTechnicalInfo)}
            >
              {showTechnicalInfo ? 'Hide Tech Info' : 'Show Tech Info'}
            </button>
          </div>
        </div>

        {error && <div className="error-message" style={{ margin: '0 24px', marginTop: '12px' }}>{error}</div>}

        {/* Phase stepper */}
        <PhaseStepper
          phases={steps}
          activePhase={activePhase}
          onSelectPhase={handleSelectPhase}
          showTechnicalInfo={showTechnicalInfo}
          phaseMap={phaseMap}
        />

        {/* Phase content */}
        {currentPhaseResult ? (
          <PhaseContentPanel
            key={activePhase}
            phase={currentPhaseResult}
            label={PHASE_LABELS[activePhase]}
            workflowId={id!}
            isCurrentPhase={workflow.current_phase === activePhase}
            showTechnicalInfo={showTechnicalInfo}
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
