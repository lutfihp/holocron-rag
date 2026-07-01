"use client";

import { useState } from "react";
import { Lock } from "lucide-react";

import { Button } from "@/components/ui/button";
import type { RefusalOut } from "@/lib/types/chat";

export function RefusalNote({ refusal }: { refusal: RefusalOut }) {
  const [copied, setCopied] = useState(false);

  async function copyRef() {
    try {
      await navigator.clipboard.writeText(refusal.reference_id);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1600);
    } catch {
      // Clipboard denied — silently no-op (demo build, no toast infrastructure).
    }
  }

  return (
    <div className="grid grid-cols-[auto_1fr_auto] items-center gap-4 p-4 bg-muted border border-dashed border-border-strong rounded-lg">
      <div className="w-10 h-10 rounded-full bg-accent text-accent-foreground grid place-items-center shrink-0">
        <Lock className="w-4 h-4" aria-hidden />
      </div>
      <div>
        <div className="text-[13px] font-semibold text-foreground">
          Some matches are above your clearance
        </div>
        <div className="text-[12px] text-muted-foreground">
          {refusal.withheld_count} higher-clearance source
          {refusal.withheld_count === 1 ? "" : "s"} may also be relevant.
        </div>
      </div>
      <div className="flex items-center gap-2 shrink-0">
        <code className="hidden sm:inline-block bg-card border border-border rounded-sm px-2 py-0.5 font-mono text-[11px] text-muted-foreground">
          REF #{refusal.reference_id}
        </code>
        <Button
          variant="outline"
          onClick={copyRef}
          className="text-[12px]"
        >
          {copied ? "Copied ✓" : "Request access"}
        </Button>
      </div>
    </div>
  );
}
