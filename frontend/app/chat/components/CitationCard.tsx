import { ClearanceBadge } from "@/components/ClearanceBadge";
import { CitationOut } from "@/lib/types/chat";

export function CitationCard({ citation }: { citation: CitationOut }) {
  return (
    <div
      id={`cite-${citation.marker}`}
      className="p-4 border border-border rounded-lg bg-card transition hover:-translate-y-0.5 hover:shadow-md hover:border-border-strong"
    >
      <div className="flex items-center justify-between mb-2">
        <span className="bg-primary text-primary-foreground rounded-md w-6 h-6 grid place-items-center font-mono text-[12px] font-semibold">
          {citation.marker}
        </span>
        <ClearanceBadge classification={citation.classification} />
      </div>
      <div className="text-[10px] font-mono uppercase tracking-[0.08em] text-subtle mb-1">
        {citation.department} · {citation.effective_date}
      </div>
      <div className="text-sm font-semibold mb-1 leading-snug">{citation.document_title}</div>
      <div className="text-[13px] text-muted-foreground leading-snug mb-2">{citation.snippet}</div>
      <div className="text-[11px] font-mono uppercase tracking-[0.08em] text-primary">
        View source ↗
      </div>
    </div>
  );
}
