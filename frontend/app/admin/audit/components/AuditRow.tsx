"use client";

import { useState } from "react";

import type { AuditRow as AuditRowType } from "@/lib/types/audit";
import { AuditEventDetail } from "./AuditEventDetail";

export function AuditRow({ row }: { row: AuditRowType }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <tr
        className="border-t cursor-pointer hover:bg-gray-50"
        onClick={() => setOpen((o) => !o)}
      >
        <td className="p-2 font-mono text-xs">
          {row.first_event_at.slice(0, 19).replace("T", " ")}
        </td>
        <td className="p-2 font-mono text-xs">{row.user_id?.slice(0, 8) ?? "—"}</td>
        <td className="p-2 text-right">{row.latency_ms} ms</td>
        <td className="p-2">
          {row.had_refusal ? (
            <span className="px-2 py-0.5 rounded bg-amber-100 text-amber-900 text-xs">
              refusal
            </span>
          ) : (
            <span className="text-gray-400">—</span>
          )}
        </td>
        <td className="p-2">
          {row.had_conflict ? (
            <span className="px-2 py-0.5 rounded bg-rose-100 text-rose-900 text-xs">
              conflict
            </span>
          ) : (
            <span className="text-gray-400">—</span>
          )}
        </td>
        <td className="p-2 text-right">{row.event_count}</td>
      </tr>
      {open && (
        <tr>
          <td colSpan={6} className="bg-gray-50 p-3">
            <div className="space-y-2">
              {row.events.map((e, i) => (
                <AuditEventDetail key={i} event={e} />
              ))}
            </div>
          </td>
        </tr>
      )}
    </>
  );
}
