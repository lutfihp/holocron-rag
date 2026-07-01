import { Lock } from "lucide-react";
import { RefusalOut } from "@/lib/types/chat";

export function RefusalNote({ refusal }: { refusal: RefusalOut }) {
  return (
    <div className="p-3 bg-muted border border-dashed border-border-strong rounded-lg text-xs text-muted-foreground flex items-start gap-2">
      <Lock className="w-3.5 h-3.5 mt-0.5 shrink-0" aria-hidden />
      <div>
        <strong>{refusal.withheld_count} higher-clearance source(s) may also be relevant.</strong>{" "}
        Request access via Reference{" "}
        <code className="bg-muted-foreground/10 px-1 py-0.5 rounded-sm text-[11px]">
          #{refusal.reference_id}
        </code>
        .
      </div>
    </div>
  );
}
