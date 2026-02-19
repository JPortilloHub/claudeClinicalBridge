import type { PhaseViewModel } from '../../types/schemas';

interface Props {
  viewModel: PhaseViewModel;
}

export default function FallbackView({ viewModel }: Props) {
  return (
    <div className="renderer-container">
      <div className="r-alert r-alert-warning">
        <h5>Structured output unavailable</h5>
        <p className="r-text-block r-text-muted">{viewModel.summary}</p>
      </div>

      {viewModel.sections.map((section, i) => (
        <div key={i} className="r-section">
          <h4 className="r-section-title">{section.title}</h4>
          <pre className="r-fallback-pre">
            {typeof section.content === 'string'
              ? section.content
              : JSON.stringify(section.content, null, 2)}
          </pre>
        </div>
      ))}
    </div>
  );
}
