import type { PhaseViewModel } from '../../types/schemas';
import KPIHeader from './KPIHeader';

interface Props {
  viewModel: PhaseViewModel;
}

export default function FallbackView({ viewModel }: Props) {
  return (
    <div className="renderer-container">
      <KPIHeader summary={viewModel.summary} kpis={viewModel.kpis} />

      {viewModel.sections.map((section, i) => (
        <div key={i} className="r-section">
          <h4 className="r-section-title">{section.title}</h4>
          <div className="r-fallback-text">
            {typeof section.content === 'string'
              ? section.content.split('\n').map((line, j) => {
                  const trimmed = line.trim();
                  if (!trimmed) return <br key={j} />;
                  // Render bullet points
                  if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
                    return <li key={j} className="r-fallback-li">{trimmed.slice(2)}</li>;
                  }
                  // Render bold text
                  if (trimmed.startsWith('**') && trimmed.endsWith('**')) {
                    return <p key={j}><strong>{trimmed.slice(2, -2)}</strong></p>;
                  }
                  return <p key={j}>{line}</p>;
                })
              : <pre className="r-fallback-pre">{JSON.stringify(section.content, null, 2)}</pre>}
          </div>
        </div>
      ))}
    </div>
  );
}
