import { clearanceBadgeClasses, clearanceLabel } from "@/lib/clearance-color";
import { Clearance } from "@/lib/types/chat";

export function ClearanceBadge({ classification }: { classification: Clearance }) {
  return (
    <span
      className={`inline-block px-1.5 py-0.5 rounded text-[10px] font-semibold border ${clearanceBadgeClasses(classification)}`}
    >
      {clearanceLabel(classification)}
    </span>
  );
}
