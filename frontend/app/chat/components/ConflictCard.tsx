import { GitCompareArrows, Scale } from "lucide-react";
import { ClearanceBadge } from "@/components/ClearanceBadge";
import type { CitationOut, ConflictOut } from "@/lib/types/chat";

export function ConflictCard({
  conflict,
  citations,
}: {
  conflict: ConflictOut;
  citations: readonly CitationOut[];
}) {
  const classA = citations.find((c) => c.marker === conflict.position_a.marker)?.classification;
  const classB = citations.find((c) => c.marker === conflict.position_b.marker)?.classification;

  return (
    <div className="border border-conflict-border rounded-lg overflow-hidden bg-card">
      {/* Header bar */}
      <div className="bg-conflict-bg px-4 py-2.5 flex items-center gap-2 border-b border-conflict-border">
        <GitCompareArrows className="w-4 h-4 text-conflict-foreground" aria-hidden />
        <div className="text-[13px] font-semibold text-conflict-foreground truncate flex-1">
          {conflict.subject}
        </div>
        <span className="px-2 py-0.5 rounded-sm bg-conflict text-conflict-foreground font-mono text-[10px] tracking-[0.08em] uppercase shrink-0">
          2 sources
        </span>
      </div>

      {/* Split-diff body: desktop = 3-col grid with spine; mobile = stacked */}
      <div className="relative grid grid-cols-1 md:grid-cols-[1fr_60px_1fr]">
        <ConflictPanel
          side="a"
          marker={conflict.position_a.marker}
          classification={classA}
          text={conflict.position_a.text}
        />
        {/* Spine + VS node (desktop only) */}
        <div className="hidden md:flex relative items-stretch justify-center">
          <div className="w-px bg-conflict-border" aria-hidden />
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-10 h-10 rounded-full bg-card border border-conflict-border shadow-sm grid place-items-center font-mono text-[10px] font-semibold tracking-[0.1em] text-conflict-foreground">
            VS
          </div>
        </div>
        {/* Mobile horizontal divider with VS node */}
        <div className="md:hidden relative flex items-center justify-center py-1 bg-muted/50">
          <div className="absolute inset-x-0 top-1/2 -translate-y-1/2 h-px bg-conflict-border" aria-hidden />
          <span className="relative bg-card px-2 rounded-sm border border-conflict-border font-mono text-[10px] font-semibold tracking-[0.1em] text-conflict-foreground">
            VS
          </span>
        </div>
        <ConflictPanel
          side="b"
          marker={conflict.position_b.marker}
          classification={classB}
          text={conflict.position_b.text}
          tinted
        />
      </div>

      {/* Footer bar */}
      <div className="bg-muted border-t border-border px-4 py-2.5 flex items-center gap-2">
        <Scale className="w-3.5 h-3.5 text-muted-foreground shrink-0" aria-hidden />
        <div className="text-[12px] text-muted-foreground">
          <span className="font-semibold text-foreground">Holocron&rsquo;s read:</span>{" "}
          The two sources disagree on <span className="italic">{conflict.subject}</span>.
        </div>
      </div>
    </div>
  );
}

function ConflictPanel({
  side,
  marker,
  classification,
  text,
  tinted = false,
}: {
  side: "a" | "b";
  marker: number;
  classification: import("@/lib/types/chat").Clearance | undefined;
  text: string;
  tinted?: boolean;
}) {
  return (
    <a
      href={`#cite-${marker}`}
      className={`block p-4 hover:bg-muted transition ${tinted ? "bg-[oklch(0.992_0.004_247)]" : ""}`}
      aria-label={`Jump to citation ${marker} (side ${side})`}
    >
      <div className="flex items-center justify-between mb-2">
        <span className="bg-accent text-accent-foreground rounded-sm px-1.5 py-0.5 font-mono text-[11px] font-semibold">
          [{marker}]
        </span>
        {classification && <ClearanceBadge classification={classification} />}
      </div>
      <div className="text-[13px] text-foreground leading-relaxed">{text}</div>
    </a>
  );
}
