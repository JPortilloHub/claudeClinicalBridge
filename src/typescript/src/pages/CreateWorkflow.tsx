import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { createWorkflow } from '../api/workflows';

export default function CreateWorkflow() {
  const navigate = useNavigate();
  const [rawNote, setRawNote] = useState('');
  const [patientId, setPatientId] = useState('');
  const [payer, setPayer] = useState('');
  const [procedure, setProcedure] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!rawNote.trim()) {
      setError('Clinical note is required');
      return;
    }
    setError('');
    setLoading(true);

    try {
      const workflow = await createWorkflow({
        raw_note: rawNote,
        patient_id: patientId || undefined,
        payer: payer || undefined,
        procedure: procedure || undefined,
        skip_prior_auth: false,
      });
      navigate(`/workflows/${workflow.id}`);
    } catch {
      setError('Failed to create workflow');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="create-workflow">
      <h1>New Workflow</h1>

      <form onSubmit={handleSubmit}>
        {error && <div className="error-message">{error}</div>}

        <div className="form-group">
          <label htmlFor="rawNote">Clinical Note *</label>
          <textarea
            id="rawNote"
            value={rawNote}
            onChange={(e) => setRawNote(e.target.value)}
            placeholder="Paste the physician's clinical note here..."
            rows={8}
            required
          />
        </div>

        <div className="form-row">
          <div className="form-group">
            <label htmlFor="patientId">Patient ID</label>
            <input
              id="patientId"
              type="text"
              value={patientId}
              onChange={(e) => setPatientId(e.target.value)}
              placeholder="Optional"
            />
          </div>

          <div className="form-group">
            <label htmlFor="payer">Payer</label>
            <input
              id="payer"
              type="text"
              value={payer}
              onChange={(e) => setPayer(e.target.value)}
              placeholder="e.g., Medicare, Aetna"
            />
          </div>

          <div className="form-group">
            <label htmlFor="procedure">Procedure</label>
            <input
              id="procedure"
              type="text"
              value={procedure}
              onChange={(e) => setProcedure(e.target.value)}
              placeholder="e.g., 99214 or MRI Brain"
            />
          </div>
        </div>

        <div className="form-actions">
          <button type="button" className="btn-secondary" onClick={() => navigate('/')}>
            Cancel
          </button>
          <button type="submit" className="btn-primary" disabled={loading}>
            {loading ? 'Creating...' : 'Create Workflow'}
          </button>
        </div>
      </form>
    </div>
  );
}
