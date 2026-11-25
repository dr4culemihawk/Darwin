"use client";

import { useState } from "react";
import type { SignalLeaf, SymbolSignal, TodaySignal as TodaySignalData } from "@/lib/data";
import { Pill } from "./ui/Pill";

const ACTION: Record<
  SymbolSignal["action"],
  { label: string; cls: string; text: string }
> = {
  enter: { label: "ENTER", cls: "border-emerald/40 bg-emerald/[0.12] text-emerald-soft", text: "text-emerald-soft" },
  exit: { label: "EXIT", cls: "border-rose/40 bg-rose/[0.12] text-rose", text: "text-rose" },
  flat: { label: "FLAT", cls: "border-white/15 bg-white/[0.04] text-zinc-400", text: "text-zinc-500" },
  unknown: { label: "N/A", cls: "border-gold/30 bg-gold/[0.08] text-gold-soft", text: "text-gold-soft" },
  no_data: { label: "NO DATA", cls: "border-white/10 bg-white/[0.03] text-zinc-500", text: "text-zinc-600" },
};

function Mark({ result }: { result: boolean | null }) {
  if (result === null)
    return <span className="text-gold-soft" title="insufficient history">?</span>;
  return result ? (
    <span className="text-emerald-soft" title="condition true">✓</span>
  ) : (
    <span className="text-zinc-600" title="condition false">✕</span>
  );
}

function Leaves({ title, leaves }: { title: string; leaves: SignalLeaf[] }) {
  return (
    <div>
      <div className="mb-1 text-[10px] font-medium uppercase tracking-[0.16em] text-zinc-600">{title}</div>
      <ul className="space-y-1">
        {leaves.map((l, i) => (
          <li key={`${l.text}-${i}`} className="flex items-baseline justify-between gap-3 text-xs">
            <span className="flex min-w-0 items-baseline gap-2">
              <Mark result={l.result} />
              <span className="truncate font-mono text-zinc-400">{l.text}</span>
            </span>
            <span className="shrink-0 font-mono text-[10px] text-zinc-600">
              {l.leftValue ?? "—"}/{l.rightValue ?? "—"}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function TodaySignal({ signal }: { signal: TodaySignalData }) {
  const firing = signal.actions.filter((a) => a.action === "enter" || a.action === "exit");
  const [open, setOpen] = useState<string | null>(firing[0]?.symbol ?? null);

  return (
    <div className="glass rounded-3xl p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="text-xs font-medium uppercase tracking-[0.16em] text-zinc-500">
            Today&apos;s champion signal
          </div>
          <p className="mt-2 text-sm leading-relaxed text-zinc-300">{signal.summary}</p>
        </div>
        <Pill className="font-mono text-[11px]">on the {signal.asOf ?? "latest"} close</Pill>
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        {signal.actions.map((a) => {
          const cls = ACTION[a.action];
          const active = open === a.symbol;
          return (
            <button
              key={a.symbol}
              type="button"
              onClick={() => setOpen(active ? null : a.symbol)}
              className={`group inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-medium transition ${
                active ? cls.cls : "border-white/10 bg-white/[0.03] text-zinc-400 hover:border-white/20"
              }`}
              aria-expanded={active}
            >
              <span className="font-mono text-zinc-200">{a.symbol}</span>
              <span className={active ? "" : cls.text}>{cls.label}</span>
            </button>
          );
        })}
      </div>

      {open && (() => {
        const a = signal.actions.find((x) => x.symbol === open);
        if (!a) return null;
        return (
          <div className="mt-4 grid gap-4 rounded-2xl border border-white/[0.06] bg-black/20 p-4 sm:grid-cols-2">
            <Leaves title="Entry rules" leaves={a.entry} />
            <Leaves title="Exit rules" leaves={a.exit} />
            <div className="sm:col-span-2 text-[11px] leading-relaxed text-zinc-500">
              Evaluated with the backtester&apos;s own condition engine on the last closed bar — the same
              rule that would place an order at the next open. Signals used:{" "}
              <span className="font-mono text-zinc-400">{signal.signalSources.join(", ") || "none"}</span>.
            </div>
          </div>
        );
      })()}
    </div>
  );
}
