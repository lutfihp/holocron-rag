import { ClearanceBadge } from "@/components/ClearanceBadge";
import { CitationOut } from "@/lib/types/chat";

export function CitationCard({ citation }: { citation: CitationOut }) {
  return (
    <div
      id={`cite-${citation.marker}`}
      className="p-3 border border-border rounded-lg bg-card"
    >
      <div className="flex items-center gap-2 mb-1">
        <span className="bg-accent text-accent-foreground px-1.5 py-0.5 rounded-sm text-[11px] font-mono font-semibold">
          [{citation.marker}]
        </span>
        <ClearanceBadge classification={citation.classification} />
        <span className="text-[10px] text-muted-foreground">
          {citation.department} · {citation.effective_date}
        </span>
      </div>
      <div className="text-xs font-semibold mb-1">{citation.document_title}</div>
      <div className="text-[11px] text-muted-foreground leading-snug">{citation.snippet}</div>
    </div>
  );
}
