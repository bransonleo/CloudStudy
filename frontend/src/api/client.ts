import type { UploadResponse, BackendMaterial, GenerateResponse, GenerationType } from '../types';

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const token = localStorage.getItem('token');
  const headers: Record<string, string> = {};

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  // Attach user's Gemini API key if available
  const geminiKey = localStorage.getItem('gemini_api_key');
  if (geminiKey) {
    headers['X-Gemini-Api-Key'] = geminiKey;
  }

  // Merge headers — don't set Content-Type for FormData (browser sets boundary)
  if (options?.headers) {
    Object.assign(headers, options.headers);
  }

  const res = await fetch(url, { ...options, headers });

  if (!res.ok) {
    const body = await res.json().catch(() => ({ error: 'Unknown error', status: res.status }));
    throw body;
  }

  return res.json();
}

export function healthCheck() {
  return request<{ status: string }>('/api/health');
}

export function uploadFile(file: File) {
  const form = new FormData();
  form.append('file', file);
  // Do NOT set Content-Type header — browser sets it with the multipart boundary
  // Backend returns 202 Accepted — res.ok is still true for 2xx
  return request<UploadResponse>('/api/upload', { method: 'POST', body: form });
}

export function generateContent(materialId: string, type: GenerationType) {
  return request<GenerateResponse>(`/api/generate/${materialId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ type }),
  });
}

export function getResults(materialId: string) {
  return request<BackendMaterial>(`/api/results/${materialId}`);
}
