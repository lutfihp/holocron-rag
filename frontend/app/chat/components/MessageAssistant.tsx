import React from "react";
import { Sparkles, TriangleAlert } from "lucide-react";
import { ChatResponse } from "@/lib/types/chat";
import { CitationChip } from "@/components/CitationChip";
import { CitationCard } from "./CitationCard";
import { ConflictCard } from "./ConflictCard";
import { RefusalNote } from "./RefusalNote";

function renderAnswerText(text: string) {
  const parts = text.split(/(\[\d+\])/);
  return parts.map((token, i) => {
    const m = token.match(/^\[(\d+)\]$/);
    if (!m) return <React.Fragment key={i}>{token}</React.Fragment>;
    const marker = parseInt(m[1], 10);
    return <CitationChip key={i} marker={marker} />;
  });
}

export function MessageAssistant({
  payload,
  latencyMs,
}: {
  payload: ChatResponse;
  latencyMs?: number;
}) {
  const nSources = payload.citations.length;
  const nConflicts = payload.conflicts.length;
  return (
    <div className="self-start w-full max-w-[95%] flex flex-col gap-3">
      <div className="bg-card rounded-lg rounded-tl-md p-4 text-sm leading-relaxed">
        <div className="flex items-center gap-2 mb-3">
          <div className="w-7 h-7 rounded-md bg-primary text-primary-foreground grid place-items-center">
            <Sparkles className="w-3.5 h-3.5" aria-hidden />
          </div>
          <div className="text-[13px] font-semibold">Holocron</div>
          <div className="text-[11px] font-mono uppercase tracking-[0.08em] text-muted-foreground ml-auto">
            {nSources} source{nSources === 1 ? "" : "s"} · {nConflicts} conflict{nConflicts === 1 ? "" : "s"}
            {latencyMs !== undefined ? ` · ${(latencyMs / 1000).toFixed(2)}s` : ""}
          </div>
        </div>
        <div className="leading-relaxed">{renderAnswerText(payload.answer.text)}</div>
      </div>

      {payload.citations.length > 0 && (
        <div>
          <div className="text-[10px] uppercase tracking-wider text-muted-foreground mb-1.5">
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
              <ConflictCard key={i} conflict={c} citations={payload.citations} />
            ))}
          </div>
        </div>
      )}

      {payload.refusal && <RefusalNote refusal={payload.refusal} />}

      {payload.answer.cited_chunk_ids.length === 0 && payload.citations.length === 0 && (
        <div className="text-[10px] text-subtle italic">
          No citations attached to this answer.
        </div>
      )}
    </div>
  );
}
