"use client";

import { useEffect, useState } from "react";
import { Activity, GitCompareArrows, Lock, type LucideIcon } from "lucide-react";

import { api } from "@/lib/api";
import type { AuditSummary } from "@/lib/types/audit-summary";

interface StatDef {
  key: keyof AuditSummary;
  label: string;
  icon: LucideIcon;
  tileClass: string;
}

const STATS: StatDef[] = [
  {
    key: "queries_today",
    label: "Queries today",
    icon: Activity,
    tileClass: "bg-accent text-accent-foreground",
  },
  {
    key: "refusals_today",
    label: "Refusals today",
    icon: Lock,
    tileClass: "bg-restricted text-restricted-foreground",
  },
  {
    key: "conflicts_today",
    label: "Conflicts today",
    icon: GitCompareArrows,
    tileClass: "bg-conflict text-conflict-foreground",
  },
];

export function SummaryStats() {
  const [data, setData] = useState<AuditSummary | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .auditSummary()
      .then((r) => {
        if (!cancelled) setData(r);
      })
      .catch((e) => {
        if (!cancelled) setError(e instanceof Error ? e.message : String(e));
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
      {STATS.map((s) => {
        const Icon = s.icon;
        const value = data ? data[s.key] : null;
        return (
          <div
            key={s.key}
            className="bg-card border border-border rounded-lg p-4 flex items-center gap-3"
          >
            <div className={`w-10 h-10 rounded-md grid place-items-center shrink-0 ${s.tileClass}`}>
              <Icon className="w-5 h-5" aria-hidden />
            </div>
            <div className="min-w-0 flex-1">
              <div className="text-[10px] font-mono uppercase tracking-[0.08em] text-subtle">
                {s.label}
              </div>
              <div className="text-[22px] font-semibold leading-tight tabular-nums">
                {value === null ? (error ? "—" : "…") : value.toLocaleString()}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
