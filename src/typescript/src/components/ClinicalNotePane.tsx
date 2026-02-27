import { useMemo } from 'react';
import type { WorkflowDetail } from '../types/api';

interface Props {
  workflow: WorkflowDetail;
  collapsed: boolean;
  onToggleCollapse: () => void;
}

interface NoteSection {
  title: string;
  lines: string[];
}

const SECTION_PATTERN = /^([A-Z][A-Z &/()-]{2,})\s*:?\s*$/;
const KV_PATTERN = /^([A-Za-z][A-Za-z /]{1,30}):\s+(.+)$/;

const SECTION_COLORS: Record<string, string> = {
  SUBJECTIVE: '#3b82f6',
  'CHIEF COMPLAINT': '#3b82f6',
  HPI: '#3b82f6',
  'HISTORY OF PRESENT ILLNESS': '#3b82f6',
  'REVIEW OF SYSTEMS': '#6366f1',
  ROS: '#6366f1',
  OBJECTIVE: '#10b981',
  VITALS: '#10b981',
  'PHYSICAL EXAM': '#10b981',
  'PHYSICAL EXAMINATION': '#10b981',
  LABS: '#0ea5e9',
  IMAGING: '#0ea5e9',
  ASSESSMENT: '#f59e0b',
  'ASSESSMENT AND PLAN': '#f59e0b',
  PLAN: '#8b5cf6',
  MEDICATIONS: '#ec4899',
  ALLERGIES: '#ef4444',
  'PAST MEDICAL HISTORY': '#64748b',
  PMH: '#64748b',
  'SOCIAL HISTORY': '#64748b',
  'FAMILY HISTORY': '#64748b',
};

function parseNote(text: string): NoteSection[] {
  const lines = text.split('\n');
  const sections: NoteSection[] = [];
  let current: NoteSection = { title: 'Note', lines: [] };

  for (const line of lines) {
    const headerMatch = line.trim().match(SECTION_PATTERN);
    if (headerMatch) {
      if (current.lines.length > 0 || sections.length === 0) {
        sections.push(current);
      }
      current = { title: headerMatch[1].trim(), lines: [] };
    } else if (line.trim()) {
      current.lines.push(line);
    }
  }

  if (current.lines.length > 0) {
    sections.push(current);
  }

  return sections.filter((s) => s.lines.length > 0);
}

function renderLine(line: string, idx: number) {
  const trimmed = line.trim();

  // Bullet point
  if (trimmed.startsWith('- ') || trimmed.startsWith('* ') || trimmed.startsWith('\u2022 ')) {
    const text = trimmed.replace(/^[-*\u2022]\s*/, '');
    return (
      <div key={idx} className="wd-note-bullet">
        <span className="wd-note-bullet-dot" />
        <span>{text}</span>
      </div>
    );
  }

  // Key: Value pair
  const kvMatch = trimmed.match(KV_PATTERN);
  if (kvMatch) {
    return (
      <div key={idx} className="wd-note-kv">
        <span className="wd-note-kv-key">{kvMatch[1]}:</span>
        <span className="wd-note-kv-val">{kvMatch[2]}</span>
      </div>
    );
  }

  // Regular text
  return <p key={idx} className="wd-note-line">{line}</p>;
}

export default function ClinicalNotePane({ workflow, collapsed, onToggleCollapse }: Props) {
  const sections = useMemo(() => parseNote(workflow.raw_note), [workflow.raw_note]);

  if (collapsed) {
    return (
      <div className="wd-note-pane wd-note-pane--collapsed" onClick={onToggleCollapse}>
        <div className="wd-note-collapsed-label">Clinical Note</div>
      </div>
    );
  }

  return (
    <div className="wd-note-pane">
      <div className="wd-note-pane-header">
        <h3>Clinical Note</h3>
        <button className="wd-note-collapse-btn" onClick={onToggleCollapse}>
          &#9664;
        </button>
      </div>
      <div className="wd-note-pane-body">
        {/* Metadata badges */}
        {(workflow.patient_id || workflow.payer || workflow.procedure) && (
          <div className="wd-note-meta-badges">
            {workflow.patient_id && (
              <span className="wd-meta-badge">
                <span className="wd-meta-badge-label">Patient</span>
                {workflow.patient_id}
              </span>
            )}
            {workflow.payer && (
              <span className="wd-meta-badge">
                <span className="wd-meta-badge-label">Payer</span>
                {workflow.payer}
              </span>
            )}
            {workflow.procedure && (
              <span className="wd-meta-badge">
                <span className="wd-meta-badge-label">Procedure</span>
                {workflow.procedure}
              </span>
            )}
          </div>
        )}

        {/* Parsed note sections */}
        <div className="wd-note-sections">
          {sections.map((section, i) => {
            const color = SECTION_COLORS[section.title.toUpperCase()] || '#94a3b8';
            return (
              <div
                key={i}
                className="wd-note-section"
                style={{ borderLeftColor: color }}
              >
                {section.title !== 'Note' && (
                  <div className="wd-note-section-title" style={{ color }}>
                    {section.title}
                  </div>
                )}
                <div className="wd-note-section-body">
                  {section.lines.map((line, j) => renderLine(line, j))}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
