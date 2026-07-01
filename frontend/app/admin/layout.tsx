"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { TopNav } from "@/components/TopNav";
import { api } from "@/lib/api";
import type { UserSummary } from "@/lib/types";

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [me, setMe] = useState<UserSummary | null>(null);
  const [allowed, setAllowed] = useState<boolean | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function check() {
      try {
        const meResp = await api.me();
        if (cancelled) return;
        setMe(meResp);
        if (meResp.role === "director" || meResp.role === "executive") setAllowed(true);
        else setAllowed(false);
      } catch {
        if (!cancelled) router.push("/login");
      }
    }
    check();
    return () => {
      cancelled = true;
    };
  }, [router]);

  if (allowed === null) {
    return <div className="p-8 text-sm text-muted-foreground">Loading admin…</div>;
  }
  if (!allowed) {
    return (
      <div className="p-8 text-sm text-destructive">
        Access denied. Admin views require director or executive role.
      </div>
    );
  }
  return (
    <>
      {me && <TopNav user={{ username: me.username, role: me.role, max_clearance: me.max_clearance }} />}
      <div className="p-8 max-w-6xl mx-auto">{children}</div>
    </>
  );
}
