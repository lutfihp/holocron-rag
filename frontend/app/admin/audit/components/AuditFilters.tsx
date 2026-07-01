"use client";

import type { AuditQuery } from "@/lib/types/audit";

interface Props {
  value: AuditQuery;
  onChange: (q: AuditQuery) => void;
}

export function AuditFilters({ value, onChange }: Props) {
  return (
    <div className="flex flex-wrap gap-3 items-end bg-muted p-3 rounded-md border border-border">
      <label className="text-sm">
        <div className="text-muted-foreground">Has refusal</div>
        <select
          value={value.has_refusal === undefined ? "" : String(value.has_refusal)}
          onChange={(e) =>
            onChange({
              ...value,
              has_refusal: e.target.value === "" ? undefined : e.target.value === "true",
            })
          }
          className="border border-border-strong rounded-md px-2 py-1"
        >
          <option value="">any</option>
          <option value="true">yes</option>
          <option value="false">no</option>
        </select>
      </label>
      <label className="text-sm">
        <div className="text-muted-foreground">Has conflict</div>
        <select
          value={value.has_conflict === undefined ? "" : String(value.has_conflict)}
          onChange={(e) =>
            onChange({
              ...value,
              has_conflict: e.target.value === "" ? undefined : e.target.value === "true",
            })
          }
          className="border border-border-strong rounded-md px-2 py-1"
        >
          <option value="">any</option>
          <option value="true">yes</option>
          <option value="false">no</option>
        </select>
      </label>
      <label className="text-sm">
        <div className="text-muted-foreground">Start</div>
        <input
          type="datetime-local"
          value={value.start ?? ""}
          onChange={(e) =>
            onChange({ ...value, start: e.target.value || undefined })
          }
          className="border border-border-strong rounded-md px-2 py-1"
        />
      </label>
      <label className="text-sm">
        <div className="text-muted-foreground">End</div>
        <input
          type="datetime-local"
          value={value.end ?? ""}
          onChange={(e) =>
            onChange({ ...value, end: e.target.value || undefined })
          }
          className="border border-border-strong rounded-md px-2 py-1"
        />
      </label>
      <button
        onClick={() => onChange({})}
        className="text-sm underline text-muted-foreground hover:text-foreground"
      >
        clear
      </button>
    </div>
  );
}
