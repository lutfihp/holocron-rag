"use client";

import { useEffect, useState } from "react";

import { fetchAuditPage } from "@/lib/audit-api";
import type {
  AuditPage,
  AuditQuery,
  AuditRow as AuditRowType,
} from "@/lib/types/audit";

import { AuditFilters } from "./components/AuditFilters";
import { AuditRow } from "./components/AuditRow";

export default function AuditViewerPage() {
  const [filters, setFilters] = useState<AuditQuery>({});
  const [rows, setRows] = useState<AuditRowType[]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function load(reset: boolean) {
    setLoading(true);
    setError(null);
    try {
      const page: AuditPage = await fetchAuditPage({
        ...filters,
        cursor: reset ? undefined : cursor ?? undefined,
      });
      setRows((prev) => (reset ? page.rows : [...prev, ...page.rows]));
      setCursor(page.next_cursor);
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setError(msg);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters]);

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Audit log</h1>
      <p className="text-sm text-gray-600">
        One row per <code>correlation_id</code> (one /chat/ask = one row). Click any
        row to inspect the underlying query, retrieved IDs, refusal ref, response,
        and conflict subjects.
      </p>
      <AuditFilters value={filters} onChange={setFilters} />
      {error && (
        <div className="border border-red-200 bg-red-50 text-red-700 rounded p-3 text-sm">
          {error}
        </div>
      )}
      <div className="border rounded overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th className="text-left p-2">Time (UTC)</th>
              <th className="text-left p-2">User</th>
              <th className="text-right p-2">Latency</th>
              <th className="text-left p-2">Refusal</th>
              <th className="text-left p-2">Conflict</th>
              <th className="text-right p-2">Events</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 && !loading && (
              <tr>
                <td colSpan={6} className="p-4 text-center text-gray-500">
                  No audit rows for the current filter.
                </td>
              </tr>
            )}
            {rows.map((r) => (
              <AuditRow key={r.correlation_id} row={r} />
            ))}
          </tbody>
        </table>
      </div>
      {cursor && (
        <button
          onClick={() => load(false)}
          disabled={loading}
          className="px-3 py-1.5 border rounded hover:bg-gray-50 text-sm"
        >
          {loading ? "Loading…" : "Load more"}
        </button>
      )}
    </div>
  );
}
