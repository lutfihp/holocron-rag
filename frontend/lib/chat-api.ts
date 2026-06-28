import { ChatResponse } from "@/lib/types/chat";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export class LLMUnavailableError extends Error {}

export async function postChatAsk(query: string): Promise<ChatResponse> {
  const res = await fetch(`${API_BASE}/chat/ask`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, top_k: 6 }),
  });
  if (res.status === 401) {
    throw new Error("unauthenticated");
  }
  if (res.status === 503) {
    throw new LLMUnavailableError("LLM temporarily unavailable. Please retry.");
  }
  if (!res.ok) {
    throw new Error(`Chat request failed: ${res.status}`);
  }
  return (await res.json()) as ChatResponse;
}
