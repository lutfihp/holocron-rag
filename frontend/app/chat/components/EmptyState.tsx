"use client";

import {
  ArrowRight,
  GitCompareArrows,
  Lock,
  MessageSquare,
  Scale,
  ScrollText,
  ShieldCheck,
  Sparkles,
  type LucideIcon,
} from "lucide-react";

import type { DemoQuestion } from "@/lib/demo-questions";

const ICONS: Record<DemoQuestion["icon"], LucideIcon> = {
  "shield-check": ShieldCheck,
  "git-compare-arrows": GitCompareArrows,
  lock: Lock,
  "message-square": MessageSquare,
  "scroll-text": ScrollText,
  scale: Scale,
};

export function EmptyState({
  questions,
  onPick,
  disabled,
}: {
  questions: readonly DemoQuestion[];
  onPick: (question: string) => void;
  disabled: boolean;
}) {
  return (
    <div className="flex-1 flex items-center justify-center p-4 sm:p-8">
      <div className="w-full max-w-3xl text-center">
        <div className="mx-auto mb-4 w-12 h-12 rounded-lg bg-accent text-accent-foreground grid place-items-center">
          <Sparkles className="w-6 h-6" aria-hidden />
        </div>
        <h2 className="text-[23px] font-semibold tracking-[-0.015em] mb-2">
          What can the archive answer for you?
        </h2>
        <p className="text-[13px] text-muted-foreground mb-8">
          Try one of these questions to see clearance-filtered retrieval, citations, and conflict detection in action.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-left">
          {questions.map((q) => {
            const Icon = ICONS[q.icon];
            return (
              <button
                key={q.question}
                type="button"
                disabled={disabled}
                onClick={() => onPick(q.question)}
                className="p-4 bg-card border border-border rounded-lg text-left transition hover:-translate-y-0.5 hover:shadow-md hover:border-border-strong disabled:opacity-50 disabled:pointer-events-none"
              >
                <div className="w-8 h-8 rounded-md bg-accent text-accent-foreground grid place-items-center mb-3">
                  <Icon className="w-4 h-4" aria-hidden />
                </div>
                <div className="text-[10px] font-mono uppercase tracking-[0.08em] text-subtle mb-1">
                  {q.category}
                </div>
                <div className="text-[13px] font-medium leading-snug mb-3">{q.question}</div>
                <div className="flex items-center gap-1 text-[11px] font-mono uppercase tracking-[0.08em] text-primary">
                  Try it <ArrowRight className="w-3 h-3" aria-hidden />
                </div>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
