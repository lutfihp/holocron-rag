"use client";

import { useEffect, useState } from "react";
import { ChevronDown, ScrollText } from "lucide-react";

import { Button } from "@/components/ui/button";
import { fetchAuditPage } from "@/lib/audit-api";
import type {
  AuditPage,
  AuditQuery,
  AuditRow as AuditRowType,
} from "@/lib/types/audit";

import { AuditFilters } from "./components/AuditFilters";
import { AuditRow } from "./components/AuditRow";
import { DataTable } from "./components/DataTable";
import { SummaryStats } from "./components/SummaryStats";

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

  const emptyStateNode = (
    <div className="flex flex-col items-center justify-center gap-2 py-14 text-center">
      <ScrollText className="w-6 h-6 text-muted-foreground" aria-hidden />
      <div className="text-[13px] text-muted-foreground">
        No audit rows for the current filter.
      </div>
    </div>
  );

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-[22px] font-semibold">Audit log</h1>
        <p className="text-[13px] text-muted-foreground mt-1">
          One row per <code className="font-mono text-[12px]">correlation_id</code> (one
          /chat/ask = one row). Click any row to inspect the underlying query,
          retrieved IDs, refusal ref, response, and conflict subjects.{" "}
          <span className="text-subtle">Director / Executive only.</span>
        </p>
      </div>

      <SummaryStats />

      <AuditFilters value={filters} onChange={setFilters} />

      {error && (
        <div className="border border-destructive/40 bg-destructive/10 text-destructive rounded-md p-3 text-sm">
          {error}
        </div>
      )}

      <DataTable isEmpty={rows.length === 0 && !loading} emptyState={emptyStateNode}>
        {rows.map((r, i) => (
          <AuditRow key={r.correlation_id} row={r} index={i} />
        ))}
      </DataTable>

      {cursor && (
        <Button variant="outline" disabled={loading} onClick={() => load(false)}>
          <ChevronDown className="w-4 h-4 mr-1" aria-hidden />
          {loading ? "Loading…" : "Load more"}
        </Button>
      )}
    </div>
  );
}
