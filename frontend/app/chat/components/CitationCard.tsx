import { ClearanceBadge } from "@/components/ClearanceBadge";
import { CitationOut } from "@/lib/types/chat";

export function CitationCard({ citation }: { citation: CitationOut }) {
  return (
    <div
      id={`cite-${citation.marker}`}
      className="p-3 border border-slate-200 rounded-lg bg-white"
    >
      <div className="flex items-center gap-2 mb-1">
        <span className="bg-blue-100 text-blue-800 px-1.5 py-0.5 rounded text-[11px] font-semibold">
          [{citation.marker}]
        </span>
        <ClearanceBadge classification={citation.classification} />
        <span className="text-[10px] text-slate-500">
          {citation.department} · {citation.effective_date}
        </span>
      </div>
      <div className="text-xs font-semibold mb-1">{citation.document_title}</div>
      <div className="text-[11px] text-slate-600 leading-snug">{citation.snippet}</div>
    </div>
  );
}
