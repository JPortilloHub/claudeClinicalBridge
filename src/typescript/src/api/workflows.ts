import client from './client';
import type { WorkflowCreate, WorkflowDetail, WorkflowSummary } from '../types/api';

export async function createWorkflow(data: WorkflowCreate): Promise<WorkflowDetail> {
  const { data: result } = await client.post<WorkflowDetail>('/api/workflows/', data);
  return result;
}

export async function listWorkflows(status?: string): Promise<WorkflowSummary[]> {
  const params = status ? { status } : {};
  const { data } = await client.get<WorkflowSummary[]>('/api/workflows/', { params });
  return data;
}

export async function getWorkflow(id: string): Promise<WorkflowDetail> {
  const { data } = await client.get<WorkflowDetail>(`/api/workflows/${id}`);
  return data;
}

export async function deleteWorkflow(id: string): Promise<void> {
  await client.delete(`/api/workflows/${id}`);
}

export async function runPhase(workflowId: string, phaseName: string): Promise<void> {
  await client.post(`/api/workflows/${workflowId}/phases/${phaseName}/run`);
}

export async function editPhaseContent(
  workflowId: string,
  phaseName: string,
  editedContent: string
): Promise<void> {
  await client.patch(`/api/workflows/${workflowId}/phases/${phaseName}`, {
    edited_content: editedContent,
  });
}

export async function approvePhase(workflowId: string, phaseName: string): Promise<{ next_phase: string | null }> {
  const { data } = await client.post(`/api/workflows/${workflowId}/phases/${phaseName}/approve`);
  return data;
}
