import type { UploadResponse, MaterialResult, GenerationType } from '../types';

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const token = localStorage.getItem('token');
  const headers: Record<string, string> = {};

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
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
  return request<UploadResponse>('/api/upload', { method: 'POST', body: form });
}

export function generateContent(materialId: string, types: GenerationType[]) {
  return request<MaterialResult>('/api/generate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ material_id: materialId, types }),
  });
}

export function getResults(materialId: string) {
  return request<MaterialResult>(`/api/results/${materialId}`);
}

export function login(email: string, password: string) {
  return request<{ token: string }>('/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });
}
