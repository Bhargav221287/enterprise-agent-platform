import { DomainPack, PackSummary, RunResponse } from '../types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export async function fetchHealth(): Promise<{ status: string; packs_loaded: number }> {
  const res = await fetch(`${API_BASE_URL}/health`);
  if (!res.ok) throw new Error(`Health check failed: ${res.statusText}`);
  return res.json();
}

export async function fetchPacks(): Promise<PackSummary[]> {
  const res = await fetch(`${API_BASE_URL}/packs`);
  if (!res.ok) throw new Error(`Failed to fetch packs: ${res.statusText}`);
  return res.json();
}

export async function fetchPackDetail(name: string): Promise<DomainPack> {
  const res = await fetch(`${API_BASE_URL}/packs/${name}`);
  if (!res.ok) throw new Error(`Failed to fetch pack '${name}': ${res.statusText}`);
  return res.json();
}

export async function fetchRuns(): Promise<RunResponse[]> {
  const res = await fetch(`${API_BASE_URL}/runs`);
  if (!res.ok) throw new Error(`Failed to fetch runs: ${res.statusText}`);
  return res.json();
}

export async function fetchRun(runId: string): Promise<RunResponse> {
  const res = await fetch(`${API_BASE_URL}/runs/${runId}`);
  if (!res.ok) throw new Error(`Failed to fetch run '${runId}': ${res.statusText}`);
  return res.json();
}

export async function createRun(payload: {
  pack_name: string;
  input_data: Record<string, any>;
  session_id?: string;
}): Promise<RunResponse> {
  const res = await fetch(`${API_BASE_URL}/runs`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Failed to start run');
  }
  return res.json();
}

export async function approveRun(
  runId: string,
  payload: { edited_output?: Record<string, any>; notes?: string }
): Promise<RunResponse> {
  const res = await fetch(`${API_BASE_URL}/runs/${runId}/approve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Failed to approve run');
  }
  return res.json();
}

export async function rejectRun(
  runId: string,
  payload: { reason: string }
): Promise<RunResponse> {
  const res = await fetch(`${API_BASE_URL}/runs/${runId}/reject`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Failed to reject run');
  }
  return res.json();
}
