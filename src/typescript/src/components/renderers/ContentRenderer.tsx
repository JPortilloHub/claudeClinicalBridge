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
 * Extract JSON from Claude's response.
 * Claude may return:
 *   1. Pure JSON: {"key": "value"}
 *   2. Fenced JSON: ```json\n{...}\n```
 *   3. Text before/after fences: "Here is the result:\n```json\n{...}\n```\nLet me know..."
 *   4. JSON embedded in prose without fences
 */
function extractJson(raw: string): string {
  const s = raw.trim();

  // Try 1: Direct JSON parse (cleanest case)
  if (s.startsWith('{') || s.startsWith('[')) {
    return s;
  }

  // Try 2: Extract from markdown fences (anywhere in the string)
  const fenceMatch = s.match(/```(?:json)?\s*\n([\s\S]*?)\n\s*```/);
  if (fenceMatch) {
    return fenceMatch[1].trim();
  }

  // Try 3: Find the first { and last } (JSON object embedded in text)
  const firstBrace = s.indexOf('{');
  const lastBrace = s.lastIndexOf('}');
  if (firstBrace !== -1 && lastBrace > firstBrace) {
    return s.slice(firstBrace, lastBrace + 1);
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
