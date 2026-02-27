import { useMemo } from 'react';
import { parsePhaseContent } from '../../utils/phaseParsers';
import FallbackView from './FallbackView';
import DocumentationView from './DocumentationView';
import CodingView from './CodingView';
import ComplianceView from './ComplianceView';
import PriorAuthView from './PriorAuthView';
import QualityView from './QualityView';

interface ContentRendererProps {
  phaseName: string;
  content: string | object;
}

export default function ContentRenderer({ phaseName, content }: ContentRendererProps) {
  const viewModel = useMemo(
    () => parsePhaseContent(phaseName, content),
    [phaseName, content],
  );

  // If parsing completely failed, show fallback
  if (viewModel.status === 'unknown') {
    return <FallbackView viewModel={viewModel} />;
  }

  const viewComponent = (() => {
    switch (phaseName) {
      case 'documentation':
        return <DocumentationView data={viewModel.raw} />;
      case 'coding':
        return <CodingView data={viewModel.raw} />;
      case 'compliance':
        return <ComplianceView data={viewModel.raw} />;
      case 'prior_auth':
        return <PriorAuthView data={viewModel.raw} />;
      case 'quality_assurance':
        return <QualityView data={viewModel.raw} />;
      default:
        return <FallbackView viewModel={viewModel} />;
    }
  })();

  return (
    <div className="r-content-renderer">
      {viewComponent}
    </div>
  );
}
