import { ConflictOut } from "@/lib/types/chat";

export function ConflictCard({ conflict }: { conflict: ConflictOut }) {
  return (
    <div className="border border-red-200 rounded-lg bg-red-50 overflow-hidden">
      <div className="px-3 py-2 bg-red-100 text-[12px] font-semibold text-red-900">
        Subject: {conflict.subject}
      </div>
      <div className="grid grid-cols-2 gap-px bg-red-200">
        <a
          href={`#cite-${conflict.position_a.marker}`}
          className="block p-3 bg-card text-[11px] hover:bg-muted"
        >
          <div className="font-semibold mb-1">[{conflict.position_a.marker}]</div>
          <div className="text-muted-foreground">{conflict.position_a.text}</div>
        </a>
        <a
          href={`#cite-${conflict.position_b.marker}`}
          className="block p-3 bg-card text-[11px] hover:bg-muted"
        >
          <div className="font-semibold mb-1">[{conflict.position_b.marker}]</div>
          <div className="text-muted-foreground">{conflict.position_b.text}</div>
        </a>
      </div>
    </div>
  );
}
