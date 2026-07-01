"use client";

import { Calendar, X } from "lucide-react";

import type { AuditQuery } from "@/lib/types/audit";

function segClasses(active: boolean, activeClass: string): string {
  const base =
    "px-3 py-1 text-[12px] font-mono uppercase tracking-[0.08em] transition first:rounded-l-sm last:rounded-r-sm";
  return active ? `${base} ${activeClass}` : `${base} bg-muted text-muted-foreground hover:text-foreground`;
}

export function AuditFilters({
  value,
  onChange,
}: {
  value: AuditQuery;
  onChange: (q: AuditQuery) => void;
}) {
  const refusalAll = value.has_refusal !== true;
  const refusalOn = value.has_refusal === true;
  const conflictAll = value.has_conflict !== true;
  const conflictOn = value.has_conflict === true;
  const hasDateRange = Boolean(value.start || value.end);
  const hasAnyFilter = refusalOn || conflictOn || hasDateRange;

  return (
    <div className="flex flex-wrap items-center gap-3 py-2">
      {/* Refusals segmented */}
      <div className="inline-flex rounded-sm border border-border overflow-hidden">
        <button
          type="button"
          onClick={() => onChange({ ...value, has_refusal: undefined })}
          className={segClasses(refusalAll, "bg-card text-foreground")}
        >
          All
        </button>
        <button
          type="button"
          onClick={() => onChange({ ...value, has_refusal: true })}
          className={segClasses(refusalOn, "bg-restricted text-restricted-foreground")}
        >
          Refusals
        </button>
      </div>

      {/* Conflicts segmented */}
      <div className="inline-flex rounded-sm border border-border overflow-hidden">
        <button
          type="button"
          onClick={() => onChange({ ...value, has_conflict: undefined })}
          className={segClasses(conflictAll, "bg-card text-foreground")}
        >
          All
        </button>
        <button
          type="button"
          onClick={() => onChange({ ...value, has_conflict: true })}
          className={segClasses(conflictOn, "bg-conflict text-conflict-foreground")}
        >
          Conflicts
        </button>
      </div>

      {/* Date range chip — inline datetime-local inputs, hidden until you focus,
          simpler than a full popover for demo. */}
      <div className="inline-flex items-center gap-2 rounded-sm border border-border px-2.5 py-1 bg-card">
        <Calendar className="w-3.5 h-3.5 text-muted-foreground" aria-hidden />
        <input
          type="datetime-local"
          value={value.start ?? ""}
          onChange={(e) => onChange({ ...value, start: e.target.value || undefined })}
          className="bg-transparent text-[12px] font-mono text-foreground outline-none"
          aria-label="Start"
        />
        <span className="text-subtle text-[12px]">→</span>
        <input
          type="datetime-local"
          value={value.end ?? ""}
          onChange={(e) => onChange({ ...value, end: e.target.value || undefined })}
          className="bg-transparent text-[12px] font-mono text-foreground outline-none"
          aria-label="End"
        />
      </div>

      {hasAnyFilter && (
        <button
          type="button"
          onClick={() => onChange({})}
          className="ml-auto inline-flex items-center gap-1 text-[12px] text-muted-foreground hover:text-foreground"
        >
          <X className="w-3 h-3" aria-hidden />
          Clear
        </button>
      )}
    </div>
  );
}
