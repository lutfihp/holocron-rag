"use client";

import { CheckCircle2, Pencil } from "lucide-react";

interface DemoAccount {
  username: string;
  tier: "Employee" | "Manager" | "Director" | "Executive";
  note: string;
}

const ACCOUNTS: readonly DemoAccount[] = [
  { username: "employee.security", tier: "Employee", note: "Sees least; great for refusal shots" },
  { username: "manager.hr", tier: "Manager", note: "Sees restricted HR docs" },
  { username: "manager.engineering", tier: "Manager", note: "Gets refusals on HR queries" },
  { username: "director.engineering", tier: "Director", note: "Sees most engineering docs" },
  { username: "director.security", tier: "Director", note: "Sees secret security docs" },
  { username: "executive.fleet", tier: "Executive", note: "Wide clearance, narrow dept" },
  { username: "executive.procurement", tier: "Executive", note: "Sees HR + procurement" },
  { username: "employee.engineering", tier: "Employee", note: "Refusals on HR + Security" },
];

export function DemoAccountPicker({
  selected,
  onPick,
  onCustom,
}: {
  /** Username of the currently-selected demo card, or null for custom. */
  selected: string | null;
  onPick: (username: string, password: string) => void;
  onCustom: () => void;
}) {
  return (
    <div className="p-6 sm:p-8 bg-muted border-t border-border rounded-b-lg">
      <div className="text-[10px] font-mono uppercase tracking-[0.1em] text-subtle mb-3">
        Demo accounts · all password imperial-march
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2">
        {ACCOUNTS.map((a) => {
          const active = a.username === selected;
          return (
            <button
              key={a.username}
              type="button"
              onClick={() => onPick(a.username, "imperial-march")}
              className={`relative text-left p-3 rounded-md bg-card border transition ${
                active
                  ? "border-primary ring-[3px] ring-accent"
                  : "border-border hover:border-border-strong hover:-translate-y-0.5"
              }`}
            >
              {active && (
                <CheckCircle2
                  className="absolute top-2 right-2 w-4 h-4 text-primary"
                  aria-hidden
                />
              )}
              <div className="font-mono text-[12px] font-semibold truncate">
                {a.username}
              </div>
              <div className="font-mono text-[10px] uppercase tracking-[0.08em] text-subtle mt-0.5">
                {a.tier}
              </div>
              <div className="text-[11px] text-muted-foreground mt-1 leading-snug">
                {a.note}
              </div>
            </button>
          );
        })}
        <button
          type="button"
          onClick={onCustom}
          className={`relative text-left p-3 rounded-md border-2 border-dashed transition flex items-center gap-2 ${
            selected === null
              ? "border-primary text-primary"
              : "border-border text-muted-foreground hover:border-border-strong hover:text-foreground"
          }`}
        >
          <Pencil className="w-4 h-4 shrink-0" aria-hidden />
          <div>
            <div className="font-mono text-[12px] font-semibold">Custom login</div>
            <div className="text-[11px] mt-0.5">Type your own credentials</div>
          </div>
        </button>
      </div>
    </div>
  );
}
