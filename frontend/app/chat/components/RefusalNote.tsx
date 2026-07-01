import { Lock } from "lucide-react";
import { RefusalOut } from "@/lib/types/chat";

export function RefusalNote({ refusal }: { refusal: RefusalOut }) {
  return (
    <div className="p-3 bg-slate-50 border border-dashed border-slate-400 rounded-lg text-xs text-slate-600 flex items-start gap-2">
      <Lock className="w-3.5 h-3.5 mt-0.5 shrink-0" aria-hidden />
      <div>
        <strong>{refusal.withheld_count} higher-clearance source(s) may also be relevant.</strong>{" "}
        Request access via Reference{" "}
        <code className="bg-slate-200 px-1 py-0.5 rounded text-[11px]">
          #{refusal.reference_id}
        </code>
        .
      </div>
    </div>
  );
}
