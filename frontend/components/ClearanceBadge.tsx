import { clearanceBadgeClasses, clearanceDotClasses, clearanceLabel } from "@/lib/clearance-color";
import { Clearance } from "@/lib/types/chat";

export function ClearanceBadge({ classification }: { classification: Clearance }) {
  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-sm text-[11px] font-mono font-semibold tracking-[0.07em] border ${clearanceBadgeClasses(classification)}`}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${clearanceDotClasses(classification)}`} aria-hidden />
      {clearanceLabel(classification)}
    </span>
  );
}
