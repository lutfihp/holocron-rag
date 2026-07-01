import { ChatResponse } from "@/lib/types/chat";
import { MessageAssistant } from "./MessageAssistant";
import { MessageUser } from "./MessageUser";

export type Turn =
  | { kind: "user"; id: string; query: string }
  | { kind: "assistant"; id: string; payload: ChatResponse }
  | { kind: "assistant-pending"; id: string }
  | { kind: "assistant-error"; id: string; message: string; previousQuery: string };

export function ChatThread({
  turns,
  onRetry,
}: {
  turns: Turn[];
  onRetry: (previousQuery: string) => void;
}) {
  return (
    <div className="flex flex-col gap-5 p-4 overflow-y-auto flex-1">
      {turns.map((t) => {
        switch (t.kind) {
          case "user":
            return <MessageUser key={t.id} query={t.query} />;
          case "assistant":
            return <MessageAssistant key={t.id} payload={t.payload} />;
          case "assistant-pending":
            return (
              <div
                key={t.id}
                className="self-start bg-muted rounded-lg rounded-tl-md p-4 text-sm text-muted-foreground animate-pulse"
              >
                Searching the archives…
              </div>
            );
          case "assistant-error":
            return (
              <div
                key={t.id}
                className="self-start border border-red-300 bg-red-50 rounded-lg p-3 text-sm text-red-800"
              >
                {t.message}
                <button
                  className="ml-3 underline text-red-900"
                  onClick={() => onRetry(t.previousQuery)}
                >
                  Retry
                </button>
              </div>
            );
        }
      })}
    </div>
  );
}
