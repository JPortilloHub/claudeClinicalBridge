interface StepDef {
  name: string;
  label: string;
  status: string;
}

interface Props {
  phases: StepDef[];
  activePhase: string;
  onSelectPhase: (name: string) => void;
}

export default function PhaseStepper({
  phases,
  activePhase,
  onSelectPhase,
}: Props) {
  return (
    <div className="wd-stepper">
      {phases.map((step, i) => {
        const isActive = step.name === activePhase;
        const statusClass = `wd-step--${step.status}`;
        const activeClass = isActive ? 'wd-step--active' : '';

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
          </div>
        );
      })}
    </div>
  );
}
