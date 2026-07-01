import type { ApiError, UserSummary } from './types';
import type { RecentQueriesResponse } from './types/user';
import type { AuditSummary } from './types/audit-summary';

const BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000';

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...(init.headers ?? {}),
    },
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      if (typeof body?.detail === 'string') detail = body.detail;
    } catch {
      // ignore JSON parse errors on error responses
    }
    const err: ApiError = { status: res.status, detail };
    throw err;
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const api = {
  login: (tenant_id: string, username: string, password: string) =>
    request<UserSummary>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ tenant_id, username, password }),
    }),
  me: () => request<UserSummary>('/auth/me'),
  logout: () => request<void>('/auth/session', { method: 'DELETE' }),
  recentQueries: (limit = 5) =>
    request<RecentQueriesResponse>(`/me/recent-queries?limit=${limit}`),
  auditSummary: () => request<AuditSummary>('/admin/audit/summary'),
};
