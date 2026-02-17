export interface User {
  id: number;
  username: string;
  full_name: string | null;
  role: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface PhaseResult {
  id: number;
  phase_name: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'skipped';
  content: string | null;
  edited_content: string | null;
  error: string | null;
  input_tokens: number | null;
  output_tokens: number | null;
  duration_seconds: number | null;
  reviewed_at: string | null;
}

export interface WorkflowSummary {
  id: string;
  created_at: string;
  status: string;
  current_phase: string | null;
  raw_note: string;
  patient_id: string | null;
  payer: string | null;
  procedure: string | null;
  total_input_tokens: number;
  total_output_tokens: number;
}

export interface WorkflowDetail extends WorkflowSummary {
  updated_at: string;
  skip_prior_auth: boolean;
  started_at: string | null;
  completed_at: string | null;
  phase_results: PhaseResult[];
}

export interface WorkflowCreate {
  raw_note: string;
  patient_id?: string;
  payer?: string;
  procedure?: string;
  skip_prior_auth?: boolean;
}
