"use client";

import type { ReactNode } from "react";

export const AUDIT_COLUMNS = "150px 1.4fr 90px 90px 90px 40px";

const HEADERS: ReadonlyArray<{ label: string; align?: "left" | "right" }> = [
  { label: "Time (UTC)" },
  { label: "User" },
  { label: "Latency", align: "right" },
  { label: "Refusal" },
  { label: "Conflict" },
  { label: "", align: "right" },
];

export function DataTable({
  isEmpty,
  emptyState,
  children,
}: {
  isEmpty: boolean;
  emptyState: ReactNode;
  children: ReactNode;
}) {
  return (
    <div className="border border-border rounded-lg overflow-hidden bg-card">
      <div className="overflow-x-auto">
        <div className="min-w-[760px]">
          {/* Sticky header */}
          <div
            className="grid bg-muted border-b border-border sticky top-0 z-10"
            style={{ gridTemplateColumns: AUDIT_COLUMNS }}
          >
            {HEADERS.map((h, i) => (
              <div
                key={i}
                className={`px-3 py-2 font-mono text-[10px] uppercase tracking-[0.1em] text-muted-foreground ${
                  h.align === "right" ? "text-right" : "text-left"
                }`}
              >
                {h.label}
              </div>
            ))}
          </div>
          {/* Body */}
          <div>
            {isEmpty ? emptyState : children}
          </div>
        </div>
      </div>
    </div>
  );
}
