import type { JobResponse, JobResult, ChatResponse } from './types';

const API_BASE = 'http://localhost:8000';

export async function startAnalysis(repoUrl: string): Promise<string> {
  const res = await fetch(`${API_BASE}/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ repo_url: repoUrl }),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || `Analysis failed: ${res.statusText}`);
  }
  const data: JobResponse = await res.json();
  return data.job_id;
}

export async function getJobResult(jobId: string): Promise<JobResult> {
  const res = await fetch(`${API_BASE}/jobs/${jobId}`);
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || `Failed to get job: ${res.statusText}`);
  }
  return await res.json();
}

export async function sendChatQuestion(jobId: string, question: string): Promise<ChatResponse> {
  const res = await fetch(`${API_BASE}/jobs/${jobId}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question }),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || `Chat failed: ${res.statusText}`);
  }
  return await res.json();
}
