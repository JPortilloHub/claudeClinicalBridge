import { useState } from 'react';
import { editPhaseContent } from '../api/workflows';

interface PhaseEditorProps {
  workflowId: string;
  phaseName: string;
  initialContent: string;
  onSave: () => void;
  onCancel: () => void;
}

export default function PhaseEditor({
  workflowId,
  phaseName,
  initialContent,
  onSave,
  onCancel,
}: PhaseEditorProps) {
  const [content, setContent] = useState(initialContent);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const handleSave = async () => {
    setSaving(true);
    setError('');
    try {
      await editPhaseContent(workflowId, phaseName, content);
      onSave();
    } catch {
      setError('Failed to save changes');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="phase-editor">
      {error && <div className="error-message">{error}</div>}
      <textarea
        value={content}
        onChange={(e) => setContent(e.target.value)}
        rows={20}
        className="editor-textarea"
      />
      <div className="editor-actions">
        <button className="btn-secondary" onClick={onCancel} disabled={saving}>
          Cancel
        </button>
        <button className="btn-primary" onClick={handleSave} disabled={saving}>
          {saving ? 'Saving...' : 'Save Changes'}
        </button>
      </div>
    </div>
  );
}
