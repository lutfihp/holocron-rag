"use client";

import { useState } from "react";

export function ChatInput({
  onSend,
  disabled,
}: {
  onSend: (q: string) => void;
  disabled: boolean;
}) {
  const [value, setValue] = useState("");

  function submit() {
    const trimmed = value.trim();
    if (!trimmed) return;
    onSend(trimmed);
    setValue("");
  }

  return (
    <div className="flex gap-2 p-3 border-t border-border">
      <textarea
        className="flex-1 resize-none border border-border-strong rounded-md p-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
        rows={2}
        placeholder="Ask the archives…"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            submit();
          }
        }}
      />
      <button
        type="button"
        className="bg-foreground text-background px-4 rounded-md text-sm disabled:bg-muted-foreground disabled:opacity-40"
        disabled={disabled || value.trim().length === 0}
        onClick={submit}
      >
        Send
      </button>
    </div>
  );
}
