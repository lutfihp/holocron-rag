"use client";

import { Suspense, useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { LLMUnavailableError, postChatAsk } from "@/lib/chat-api";
import { TopNav } from "@/components/TopNav";
import { getDemoQuestions } from "@/lib/demo-questions";
import { Clearance } from "@/lib/types/chat";
import { ChatInput } from "./components/ChatInput";
import { ChatThread, Turn } from "./components/ChatThread";
import { EmptyState } from "./components/EmptyState";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

interface MeResponse {
  id: string;
  username: string;
  role: string;
  max_clearance: Clearance;
  departments: string[];
  tenant: { id: string; name: string; role_label: string };
}

let _idCounter = 0;
function nextId() {
  _idCounter += 1;
  return `t${_idCounter}`;
}

function ChatPageInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [me, setMe] = useState<MeResponse | null>(null);
  const [turns, setTurns] = useState<Turn[]>([]);
  const [sending, setSending] = useState(false);
  const bottomRef = useRef<HTMLDivElement | null>(null);
  const prefillOnceRef = useRef(false);

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
    const startedAt = performance.now();
    try {
      const payload = await postChatAsk(query);
      const latencyMs = Math.round(performance.now() - startedAt);
      setTurns((t) =>
        t.map((x) =>
          x.id === pendingTurn.id
            ? { kind: "assistant", id: x.id, payload, latencyMs }
            : x
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

  useEffect(() => {
    if (prefillOnceRef.current || !me) return;
    const q = searchParams.get("q");
    if (q && q.trim()) {
      prefillOnceRef.current = true;
      send(q.trim());
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [me, searchParams]);

  if (!me) {
    return <div className="p-6 text-sm text-muted-foreground">Loading…</div>;
  }

  return (
    <div className="flex flex-col h-screen">
      <TopNav user={{ username: me.username, role: me.role, max_clearance: me.max_clearance }} />

      {turns.length === 0 ? (
        <EmptyState
          questions={getDemoQuestions(me.departments)}
          onPick={send}
          disabled={sending}
        />
      ) : (
        <ChatThread turns={turns} onRetry={(q) => send(q)} />
      )}
      <div ref={bottomRef} />

      <ChatInput onSend={send} disabled={sending} />
    </div>
  );
}

export default function ChatPage() {
  return (
    <Suspense fallback={<div className="p-6 text-sm text-muted-foreground">Loading…</div>}>
      <ChatPageInner />
    </Suspense>
  );
}
