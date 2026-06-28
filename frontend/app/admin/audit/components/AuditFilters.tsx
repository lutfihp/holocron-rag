"use client";

import type { AuditQuery } from "@/lib/types/audit";

interface Props {
  value: AuditQuery;
  onChange: (q: AuditQuery) => void;
}

export function AuditFilters({ value, onChange }: Props) {
  return (
    <div className="flex flex-wrap gap-3 items-end bg-gray-50 p-3 rounded border">
      <label className="text-sm">
        <div className="text-gray-600">Has refusal</div>
        <select
          value={value.has_refusal === undefined ? "" : String(value.has_refusal)}
          onChange={(e) =>
            onChange({
              ...value,
              has_refusal: e.target.value === "" ? undefined : e.target.value === "true",
            })
          }
          className="border rounded px-2 py-1"
        >
          <option value="">any</option>
          <option value="true">yes</option>
          <option value="false">no</option>
        </select>
      </label>
      <label className="text-sm">
        <div className="text-gray-600">Has conflict</div>
        <select
          value={value.has_conflict === undefined ? "" : String(value.has_conflict)}
          onChange={(e) =>
            onChange({
              ...value,
              has_conflict: e.target.value === "" ? undefined : e.target.value === "true",
            })
          }
          className="border rounded px-2 py-1"
        >
          <option value="">any</option>
          <option value="true">yes</option>
          <option value="false">no</option>
        </select>
      </label>
      <label className="text-sm">
        <div className="text-gray-600">Start</div>
        <input
          type="datetime-local"
          value={value.start ?? ""}
          onChange={(e) =>
            onChange({ ...value, start: e.target.value || undefined })
          }
          className="border rounded px-2 py-1"
        />
      </label>
      <label className="text-sm">
        <div className="text-gray-600">End</div>
        <input
          type="datetime-local"
          value={value.end ?? ""}
          onChange={(e) =>
            onChange({ ...value, end: e.target.value || undefined })
          }
          className="border rounded px-2 py-1"
        />
      </label>
      <button
        onClick={() => onChange({})}
        className="text-sm underline text-gray-600 hover:text-gray-900"
      >
        clear
      </button>
    </div>
  );
}
