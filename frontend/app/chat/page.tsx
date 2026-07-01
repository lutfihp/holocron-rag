"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { LLMUnavailableError, postChatAsk } from "@/lib/chat-api";
import { TopNav } from "@/components/TopNav";
import { Clearance } from "@/lib/types/chat";
import { ChatInput } from "./components/ChatInput";
import { ChatThread, Turn } from "./components/ChatThread";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

interface MeResponse {
  id: string;
  username: string;
  role: string;
  max_clearance: Clearance;
  departments: string[];
  tenant: { id: string; name: string; role_label: string };
}

const SUGGESTED = [
  "What's the dress-code policy for off-base events?",
  "What is the reactor coolant shutdown sequence?",
];

let _idCounter = 0;
function nextId() {
  _idCounter += 1;
  return `t${_idCounter}`;
}

export default function ChatPage() {
  const router = useRouter();
  const [me, setMe] = useState<MeResponse | null>(null);
  const [turns, setTurns] = useState<Turn[]>([]);
  const [sending, setSending] = useState(false);
  const bottomRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    (async () => {
      const res = await fetch(`${API_BASE}/auth/me`, { credentials: "include" });
      if (res.status === 401) {
        router.replace("/login?next=/chat");
        return;
      }
      if (!res.ok) return;
      setMe((await res.json()) as MeResponse);
    })();
  }, [router]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [turns]);

  async function send(query: string) {
    const userTurn: Turn = { kind: "user", id: nextId(), query };
    const pendingTurn: Turn = { kind: "assistant-pending", id: nextId() };
    setTurns((t) => [...t, userTurn, pendingTurn]);
    setSending(true);
    try {
      const payload = await postChatAsk(query);
      setTurns((t) =>
        t.map((x) =>
          x.id === pendingTurn.id ? { kind: "assistant", id: x.id, payload } : x
        )
      );
    } catch (e) {
      const msg =
        e instanceof LLMUnavailableError
          ? "LLM temporarily unavailable. Please retry."
          : (e as Error).message === "unauthenticated"
          ? "Session expired. Please log in again."
          : "Request failed. Please retry.";
      setTurns((t) =>
        t.map((x) =>
          x.id === pendingTurn.id
            ? { kind: "assistant-error", id: x.id, message: msg, previousQuery: query }
            : x
        )
      );
      if ((e as Error).message === "unauthenticated") {
        router.replace("/login?next=/chat");
      }
    } finally {
      setSending(false);
    }
  }

  if (!me) {
    return <div className="p-6 text-sm text-muted-foreground">Loading…</div>;
  }

  return (
    <div className="flex flex-col h-screen">
      <TopNav user={{ username: me.username, role: me.role, max_clearance: me.max_clearance }} />

      {turns.length === 0 ? (
        <div className="flex-1 flex items-center justify-center p-4">
          <div className="max-w-md text-center w-full">
            <div className="mb-4 text-sm text-muted-foreground">
              Welcome, {me.tenant.role_label}. Try a question:
            </div>
            <div className="flex flex-col gap-2">
              {SUGGESTED.map((q) => (
                <button
                  key={q}
                  type="button"
                  className="border border-border rounded-lg px-3 py-2 text-sm text-left hover:bg-muted"
                  onClick={() => send(q)}
                  disabled={sending}
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        </div>
      ) : (
        <ChatThread turns={turns} onRetry={(q) => send(q)} />
      )}
      <div ref={bottomRef} />

      <ChatInput onSend={send} disabled={sending} />
    </div>
  );
}
