import type { AuditPage, AuditQuery } from "./types/audit";

const BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export async function fetchAuditPage(q: AuditQuery): Promise<AuditPage> {
  const params = new URLSearchParams();
  for (const [k, v] of Object.entries(q)) {
    if (v !== undefined && v !== null && v !== "") {
      params.set(k, String(v));
    }
  }
  const res = await fetch(`${BASE}/admin/audit?${params.toString()}`, {
    credentials: "include",
  });
  if (res.status === 401) throw new Error("Not signed in.");
  if (res.status === 403) throw new Error("Director or executive role required.");
  if (!res.ok) throw new Error(`Audit fetch failed: HTTP ${res.status}`);
  return res.json();
}
