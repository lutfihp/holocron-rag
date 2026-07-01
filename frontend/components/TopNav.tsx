"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Database } from "lucide-react";

import { ClearanceBadge } from "@/components/ClearanceBadge";
import type { Clearance } from "@/lib/types/chat";

export interface TopNavUser {
  username: string;
  role: string;
  max_clearance: Clearance;
}

interface TabDef {
  href: string;
  label: string;
  match: (pathname: string) => boolean;
  requiresAdmin?: boolean;
}

const TABS: TabDef[] = [
  { href: "/me", label: "Home", match: (p) => p === "/me" || p === "/" },
  { href: "/chat", label: "Chat", match: (p) => p.startsWith("/chat") },
  { href: "/admin/audit", label: "Audit log", match: (p) => p.startsWith("/admin"), requiresAdmin: true },
];

function initials(username: string): string {
  const [head, tail] = username.split(".");
  const first = head?.[0] ?? "";
  const second = tail?.[0] ?? head?.[1] ?? "";
  return (first + second).toUpperCase() || "?";
}

export function TopNav({ user }: { user: TopNavUser }) {
  const pathname = usePathname();
  const isAdmin = user.role === "director" || user.role === "executive";
  const tabs = TABS.filter((t) => (t.requiresAdmin ? isAdmin : true));

  return (
    <header className="h-[62px] bg-card border-b border-border flex items-center gap-6 px-6">
      <Link href="/me" className="flex items-center gap-2 font-mono text-[13px] font-semibold tracking-[0.18em]">
        <Database className="w-4 h-4 text-primary" aria-hidden />
        HOLOCRON
      </Link>
      <div className="w-px h-5 bg-border" aria-hidden />
      <nav className="flex items-center gap-1">
        {tabs.map((t) => {
          const active = t.match(pathname);
          return (
            <Link
              key={t.href}
              href={t.href}
              className={`px-3 py-2 text-sm relative ${
                active ? "text-foreground font-medium" : "text-muted-foreground hover:text-foreground"
              }`}
            >
              {t.label}
              {active && (
                <span className="absolute left-3 right-3 -bottom-[1px] h-[2px] bg-primary" aria-hidden />
              )}
            </Link>
          );
        })}
      </nav>
      <div className="ml-auto flex items-center gap-3">
        <ClearanceBadge classification={user.max_clearance} />
        <div className="w-8 h-8 rounded-full bg-accent text-accent-foreground grid place-items-center font-mono text-[11px] font-semibold">
          {initials(user.username)}
        </div>
      </div>
    </header>
  );
}
