"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { CornerDownRight, History } from "lucide-react";

import { api } from "@/lib/api";
import type { RecentQueryItem } from "@/lib/types/user";

function relativeTime(iso: string): string {
  const d = new Date(iso);
  const diffMs = Date.now() - d.getTime();
  const s = Math.max(0, Math.floor(diffMs / 1000));
  if (s < 60) return `${s}s`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h`;
  const days = Math.floor(h / 24);
  return `${days}d`;
}

export function RecentQueries() {
  const [items, setItems] = useState<RecentQueryItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .recentQueries(5)
      .then((r) => {
        if (!cancelled) setItems(r.items);
      })
      .catch((e) => {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : String(e));
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="bg-card border border-border rounded-lg p-4">
      <div className="flex items-center gap-2 mb-3">
        <History className="w-4 h-4 text-muted-foreground" aria-hidden />
        <div className="text-[13px] font-semibold">Recent queries</div>
      </div>
      {items === null && !error && (
        <div className="text-[13px] text-muted-foreground">Loading…</div>
      )}
      {error && (
        <div className="text-[13px] text-muted-foreground">
          Couldn&rsquo;t load recent activity.
        </div>
      )}
      {items && items.length === 0 && (
        <div className="text-[13px] text-muted-foreground">
          No queries yet. Try one from the panel on the right.
        </div>
      )}
      {items && items.length > 0 && (
        <ul className="flex flex-col gap-1">
          {items.map((it) => (
            <li key={it.correlation_id}>
              <Link
                href={`/chat?q=${encodeURIComponent(it.query)}`}
                className="group flex items-start gap-2 p-2 -mx-2 rounded-md hover:bg-muted transition"
              >
                <span className="w-12 shrink-0 font-mono text-[11px] text-subtle mt-0.5">
                  {relativeTime(it.occurred_at)}
                </span>
                <CornerDownRight className="w-3.5 h-3.5 text-subtle shrink-0 mt-0.5" aria-hidden />
                <span className="text-[13px] text-foreground truncate group-hover:text-foreground">
                  {it.query}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
