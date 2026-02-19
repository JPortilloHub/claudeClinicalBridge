import type { PhaseResult } from '../types/api';

interface StepDef {
  name: string;
  label: string;
  status: string;
}

interface Props {
  phases: StepDef[];
  activePhase: string;
  onSelectPhase: (name: string) => void;
  showTechnicalInfo: boolean;
  phaseMap: Record<string, PhaseResult>;
}

export default function PhaseStepper({
  phases,
  activePhase,
  onSelectPhase,
  showTechnicalInfo,
  phaseMap,
}: Props) {
  return (
    <div className={`wd-stepper ${showTechnicalInfo ? 'wd-stepper--show-technical' : ''}`}>
      {phases.map((step, i) => {
        const isActive = step.name === activePhase;
        const statusClass = `wd-step--${step.status}`;
        const activeClass = isActive ? 'wd-step--active' : '';
        const phaseResult = phaseMap[step.name];

        return (
          <div
            key={step.name}
            className={`wd-step ${statusClass} ${activeClass}`}
            onClick={() => onSelectPhase(step.name)}
          >
            <div className="wd-step-circle">
              {step.status === 'completed' ? '\u2713' : i + 1}
            </div>
            <span className="wd-step-label">{step.label}</span>
            {phaseResult && (
              <span className="wd-step-meta">
                {phaseResult.duration_seconds
                  ? `${phaseResult.duration_seconds.toFixed(1)}s`
                  : ''}
                {phaseResult.input_tokens && phaseResult.output_tokens
                  ? ` · ${(phaseResult.input_tokens + phaseResult.output_tokens).toLocaleString()} tok`
                  : ''}
              </span>
            )}
          </div>
        );
      })}
    </div>
  );
}
