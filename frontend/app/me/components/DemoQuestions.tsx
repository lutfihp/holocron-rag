"use client";

import Link from "next/link";
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

import { getDemoQuestions, type DemoQuestion } from "@/lib/demo-questions";

const ICONS: Record<DemoQuestion["icon"], LucideIcon> = {
  "shield-check": ShieldCheck,
  "git-compare-arrows": GitCompareArrows,
  lock: Lock,
  "message-square": MessageSquare,
  "scroll-text": ScrollText,
  scale: Scale,
};

export function DemoQuestions({ departments }: { departments: readonly string[] }) {
  const questions = getDemoQuestions(departments);
  return (
    <div className="bg-card border border-border rounded-lg p-4">
      <div className="flex items-center gap-2 mb-3">
        <Sparkles className="w-4 h-4 text-muted-foreground" aria-hidden />
        <div className="text-[13px] font-semibold">Try a demo question</div>
      </div>
      <ul className="flex flex-col gap-1">
        {questions.map((q) => {
          const Icon = ICONS[q.icon];
          return (
            <li key={q.question}>
              <Link
                href={`/chat?q=${encodeURIComponent(q.question)}`}
                className="group flex items-center gap-3 p-2 -mx-2 rounded-md hover:bg-muted hover:translate-x-0.5 transition"
              >
                <div className="w-8 h-8 rounded-md bg-accent text-accent-foreground grid place-items-center shrink-0">
                  <Icon className="w-4 h-4" aria-hidden />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="text-[10px] font-mono uppercase tracking-[0.08em] text-subtle">
                    {q.category}
                  </div>
                  <div className="text-[13px] font-medium truncate">{q.question}</div>
                </div>
                <ArrowRight className="w-4 h-4 text-muted-foreground shrink-0 group-hover:text-primary" aria-hidden />
              </Link>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
