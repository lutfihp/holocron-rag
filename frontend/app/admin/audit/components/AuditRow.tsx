"use client";

import { useState } from "react";
import { ChevronRight } from "lucide-react";

import type { AuditRow as AuditRowType } from "@/lib/types/audit";
import { initials } from "@/lib/initials";

import { AuditEventDetail } from "./AuditEventDetail";
import { AUDIT_COLUMNS } from "./DataTable";

export function AuditRow({ row, index }: { row: AuditRowType; index: number }) {
  const [open, setOpen] = useState(false);
  const zebra = index % 2 === 1 ? "bg-[oklch(0.988_0.003_247)]" : "";
  const activeTint = open ? "bg-accent" : "";
  const shortUser = row.user_id?.slice(0, 8) ?? "—";
  return (
    <div className="border-b border-border last:border-b-0">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className={`w-full grid text-left ${zebra} ${activeTint} hover:bg-muted transition`}
        style={{ gridTemplateColumns: AUDIT_COLUMNS }}
        aria-expanded={open}
      >
        <div className="px-3 py-2 font-mono text-[12px] text-foreground">
          {row.first_event_at.slice(0, 19).replace("T", " ")}
        </div>
        <div className="px-3 py-2 flex items-center gap-2 min-w-0">
          <div className="w-6 h-6 rounded-full bg-accent text-accent-foreground grid place-items-center font-mono text-[10px] font-semibold shrink-0">
            {initials(shortUser)}
          </div>
          <span className="font-mono text-[12px] truncate">{shortUser}</span>
        </div>
        <div className="px-3 py-2 text-right font-mono text-[12px] text-muted-foreground">
          {row.latency_ms} ms
        </div>
        <div className="px-3 py-2">
          {row.had_refusal ? (
            <span className="px-2 py-0.5 rounded-sm bg-restricted text-restricted-foreground font-mono text-[10px] uppercase tracking-[0.08em]">
              yes
            </span>
          ) : (
            <span className="px-2 py-0.5 rounded-sm bg-muted text-muted-foreground font-mono text-[10px] uppercase tracking-[0.08em]">
              no
            </span>
          )}
        </div>
        <div className="px-3 py-2">
          {row.had_conflict ? (
            <span className="px-2 py-0.5 rounded-sm bg-conflict text-conflict-foreground font-mono text-[10px] uppercase tracking-[0.08em]">
              yes
            </span>
          ) : (
            <span className="px-2 py-0.5 rounded-sm bg-muted text-muted-foreground font-mono text-[10px] uppercase tracking-[0.08em]">
              no
            </span>
          )}
        </div>
        <div className="px-3 py-2 flex items-center justify-end">
          <ChevronRight
            className={`w-4 h-4 text-muted-foreground transition-transform ${
              open ? "rotate-90" : ""
            }`}
            aria-hidden
          />
        </div>
      </button>
      {open && (
        <div className="bg-muted px-4 py-3 border-t border-border space-y-2">
          {row.events.map((e, i) => (
            <AuditEventDetail key={i} event={e} />
          ))}
        </div>
      )}
    </div>
  );
}
