import type { Regime, RegimeComponent } from "@/lib/data";

const TONE = {
  "risk-on": { text: "text-emerald-soft", border: "border-emerald/30", bg: "bg-emerald/[0.08]", dot: "bg-emerald", stroke: "#10B981" },
  "risk-off": { text: "text-rose", border: "border-rose/30", bg: "bg-rose/[0.08]", dot: "bg-rose", stroke: "#F43F5E" },
  neutral: { text: "text-gold-soft", border: "border-gold/30", bg: "bg-gold/[0.08]", dot: "bg-gold", stroke: "#F0B90B" },
} as const;

function money(v: number | null): string {
  if (v == null) return "n/a";
  const a = Math.abs(v);
  if (a >= 1e12) return `$${(v / 1e12).toFixed(2)}T`;
  if (a >= 1e9) return `$${(v / 1e9).toFixed(2)}B`;
  if (a >= 1e6) return `$${(v / 1e6).toFixed(1)}M`;
  return `$${v.toFixed(0)}`;
}

function fmt(c: RegimeComponent): string {
  const v = c.value;
  if (v == null) return "n/a";
  switch (c.format) {
    case "usd":
      return c.digits === 0 && Math.abs(v) > 1e9 ? money(v) : `$${v.toLocaleString("en-US", { maximumFractionDigits: c.digits })}`;
    case "pct":
      return `${v.toFixed(c.digits)}%`;
    case "pp":
      return `${v >= 0 ? "+" : ""}${v.toFixed(c.digits)}pp`;
    default:
      return v.toLocaleString("en-US", { maximumFractionDigits: c.digits });
  }
}

/** Sparkline of BTC dominance with the neutral band drawn as a reference. */
function DominanceSpark({ points, stroke }: { points: number[]; stroke: string }) {
  if (points.length < 2) return null;
  const w = 320;
  const h = 64;
  const min = Math.min(...points);
  const max = Math.max(...points);
  const span = max - min || 1;
  const x = (i: number) => (i / (points.length - 1)) * w;
  const y = (v: number) => h - ((v - min) / span) * (h - 8) - 4;
  const d = points.map((v, i) => `${i === 0 ? "M" : "L"} ${x(i).toFixed(2)} ${y(v).toFixed(2)}`).join(" ");
  const area = `${d} L ${w} ${h} L 0 ${h} Z`;
  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="w-full" preserveAspectRatio="none" aria-hidden>
      <defs>
        <linearGradient id="dom-fill" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={stroke} stopOpacity="0.28" />
          <stop offset="100%" stopColor={stroke} stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={area} fill="url(#dom-fill)" />
      <path d={d} fill="none" stroke={stroke} strokeWidth="1.75" strokeLinejoin="round" strokeLinecap="round" />
      <circle cx={x(points.length - 1)} cy={y(points[points.length - 1])} r="3" fill={stroke} />
    </svg>
  );
}

export function RegimeRadar({ regime }: { regime: Regime }) {
  const tone = TONE[regime.tone] ?? TONE.neutral;
  const dom = regime.history
    .map((p) => p.btcDominance)
    .filter((v): v is number => v != null);
  const first = dom[0];
  const last = dom[dom.length - 1];

  return (
    <div className="grid gap-5 lg:grid-cols-5">
      <div className="glass rounded-3xl p-6 lg:col-span-2">
        <div className="flex items-center justify-between gap-3">
          <div className="text-xs font-medium uppercase tracking-[0.16em] text-zinc-500">
            Cross-market regime
          </div>
          <span
            className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-medium ${tone.border} ${tone.bg} ${tone.text}`}
          >
            <span className={`h-1.5 w-1.5 rounded-full ${tone.dot}`} />
            {regime.tone}
          </span>
        </div>

        <h3 className="mt-4 text-balance text-xl font-semibold tracking-tight text-white">
          {regime.label}
        </h3>
        <p className="mt-2 text-sm leading-relaxed text-zinc-400">{regime.note}</p>

        {dom.length > 1 && (
          <div className="mt-5">
            <div className="mb-1.5 flex items-baseline justify-between text-xs text-zinc-500">
              <span>BTC dominance · {regime.history.length}d</span>
              <span className="font-mono text-zinc-300">
                {first.toFixed(2)}% → {last.toFixed(2)}%
              </span>
            </div>
            <DominanceSpark points={dom} stroke={tone.stroke} />
          </div>
        )}

        <div className="mt-5 flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-zinc-500">
          <span>as of {regime.asOf ?? "n/a"}</span>
          <span className="text-zinc-700">·</span>
          <span>{regime.source}</span>
          {Object.entries(regime.provenance).map(([k, v]) => (
            <span key={k} className="rounded bg-white/[0.04] px-1.5 py-0.5 font-mono text-[10px] text-zinc-400">
              {k}:{v === "CoinMarketCap" ? "cmc" : v}
            </span>
          ))}
        </div>
      </div>

      <div className="glass rounded-3xl p-6 lg:col-span-3">
        <div className="text-xs font-medium uppercase tracking-[0.16em] text-zinc-500">
          What the numbers say
        </div>
        <ul className="mt-4 divide-y divide-white/[0.06]">
          {regime.components.map((c) => (
            <li key={c.name} className="flex items-start justify-between gap-4 py-3 first:pt-0 last:pb-0">
              <div className="min-w-0">
                <div className="text-sm font-medium text-zinc-200">{c.name}</div>
                <div className="mt-0.5 text-xs leading-relaxed text-zinc-500">{c.reading}</div>
                <div className="mt-1 truncate font-mono text-[10px] text-zinc-600">{c.endpoint}</div>
              </div>
              <div className="shrink-0 text-right">
                <div className="font-mono text-sm text-white">{fmt(c)}</div>
              </div>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
