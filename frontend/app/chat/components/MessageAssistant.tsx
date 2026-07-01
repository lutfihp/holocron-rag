import React from "react";
import { TriangleAlert } from "lucide-react";
import { ChatResponse } from "@/lib/types/chat";
import { CitationCard } from "./CitationCard";
import { ConflictCard } from "./ConflictCard";
import { RefusalNote } from "./RefusalNote";

function renderAnswerText(text: string) {
  const parts = text.split(/(\[\d+\])/);
  return parts.map((token, i) => {
    const m = token.match(/^\[(\d+)\]$/);
    if (!m) return <React.Fragment key={i}>{token}</React.Fragment>;
    const marker = parseInt(m[1], 10);
    return (
      <a
        key={i}
        href={`#cite-${marker}`}
        className="bg-blue-100 text-blue-800 px-1.5 py-0.5 rounded text-[11px] font-semibold mx-0.5 hover:bg-blue-200"
      >
        [{marker}]
      </a>
    );
  });
}

export function MessageAssistant({ payload }: { payload: ChatResponse }) {
  return (
    <div className="self-start w-full max-w-[95%] flex flex-col gap-3">
      <div className="bg-slate-50 rounded-2xl rounded-tl-md p-4 text-sm leading-relaxed">
        {renderAnswerText(payload.answer.text)}
      </div>

      {payload.citations.length > 0 && (
        <div>
          <div className="text-[10px] uppercase tracking-wider text-slate-500 mb-1.5">
            Citations · {payload.citations.length}
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
            {payload.citations.map((c) => (
              <CitationCard key={c.marker} citation={c} />
            ))}
          </div>
        </div>
      )}

      {payload.conflicts.length > 0 && (
        <div>
          <div className="text-[10px] uppercase tracking-wider text-red-700 mb-1.5 flex items-center gap-1">
            <TriangleAlert className="w-3 h-3" aria-hidden />
            Conflicts detected · {payload.conflicts.length}
          </div>
          <div className="flex flex-col gap-2">
            {payload.conflicts.map((c, i) => (
              <ConflictCard key={i} conflict={c} />
            ))}
          </div>
        </div>
      )}

      {payload.refusal && <RefusalNote refusal={payload.refusal} />}

      {payload.answer.cited_chunk_ids.length === 0 && payload.citations.length === 0 && (
        <div className="text-[10px] text-slate-400 italic">
          No citations attached to this answer.
        </div>
      )}
    </div>
  );
}
