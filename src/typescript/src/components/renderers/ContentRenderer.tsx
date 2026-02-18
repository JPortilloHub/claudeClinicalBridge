import DocumentationView from './DocumentationView';
import CodingView from './CodingView';
import ComplianceView from './ComplianceView';
import PriorAuthView from './PriorAuthView';
import QualityView from './QualityView';

interface ContentRendererProps {
  phaseName: string;
  content: string;
}

/**
 * Strip markdown code fences if present.
 * Claude often returns JSON wrapped in ```json ... ``` blocks.
 */
function extractJson(raw: string): string {
  let s = raw.trim();
  // Match ```json ... ``` or ``` ... ```
  const fenceMatch = s.match(/^```(?:json)?\s*\n?([\s\S]*?)\n?\s*```$/);
  if (fenceMatch) {
    s = fenceMatch[1].trim();
  }
  return s;
}

export default function ContentRenderer({ phaseName, content }: ContentRendererProps) {
  const cleaned = extractJson(content);

  let parsed: unknown;
  try {
    parsed = JSON.parse(cleaned);
  } catch {
    return <pre className="phase-content">{content}</pre>;
  }

  if (typeof parsed !== 'object' || parsed === null) {
    return <pre className="phase-content">{content}</pre>;
  }

  /* eslint-disable @typescript-eslint/no-explicit-any */
  const data = parsed as any;

  switch (phaseName) {
    case 'documentation':
      return <DocumentationView data={data} />;
    case 'coding':
      return <CodingView data={data} />;
    case 'compliance':
      return <ComplianceView data={data} />;
    case 'prior_auth':
      return <PriorAuthView data={data} />;
    case 'quality_assurance':
      return <QualityView data={data} />;
    default:
      return <pre className="phase-content">{JSON.stringify(data, null, 2)}</pre>;
  }
}
