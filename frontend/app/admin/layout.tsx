"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { api } from "@/lib/api";

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [allowed, setAllowed] = useState<boolean | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function check() {
      try {
        const me = await api.me();
        if (cancelled) return;
        const role = (me as { role?: string }).role;
        if (role === "director" || role === "executive") setAllowed(true);
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
    return <div className="p-8 text-sm text-gray-500">Loading admin…</div>;
  }
  if (!allowed) {
    return (
      <div className="p-8 text-sm text-red-700">
        Access denied. Admin views require director or executive role.
      </div>
    );
  }
  return <div className="p-8 max-w-6xl mx-auto">{children}</div>;
}
