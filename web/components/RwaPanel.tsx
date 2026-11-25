import type { Rwa } from "@/lib/data";

function money(v: number | null): string {
  if (v == null) return "n/a";
  const a = Math.abs(v);
  if (a >= 1e12) return `$${(v / 1e12).toFixed(2)}T`;
  if (a >= 1e9) return `$${(v / 1e9).toFixed(2)}B`;
  if (a >= 1e6) return `$${(v / 1e6).toFixed(1)}M`;
  if (a >= 1e3) return `$${(v / 1e3).toFixed(1)}K`;
  return `$${v.toFixed(0)}`;
}

function pct(v: number | null, digits = 1): string {
  if (v == null) return "n/a";
  return `${v >= 0 ? "+" : ""}${v.toFixed(digits)}%`;
}

export function RwaPanel({ rwa }: { rwa: Rwa }) {
  const a = rwa.asset;
  const issuers = rwa.issuers.filter((i) => (i.marketCap ?? 0) > 0);
  const top = issuers[0];
  const rest = rwa.leaderboard.filter((r) => r.symbol !== a.symbol).slice(0, 5);

  return (
    <div className="grid gap-5 lg:grid-cols-5">
      <div className="glass rounded-3xl p-6 lg:col-span-2">
        <div className="text-xs font-medium uppercase tracking-[0.16em] text-zinc-500">
          Tokenized gold — the safe haven, on-chain
        </div>
        <div className="mt-4 flex items-end justify-between gap-3">
          <div>
            <div className="font-mono text-3xl font-semibold text-white">{money(a.price)}</div>
            <div className="mt-1 text-xs text-zinc-500">
              per tokenized {a.name ?? a.symbol} · 30d{" "}
              <span className={(a.change30d ?? 0) >= 0 ? "text-emerald-soft" : "text-rose"}>
                {pct(a.change30d)}
              </span>
            </div>
          </div>
          <div className="text-right">
            <div className="font-mono text-sm text-zinc-200">{money(a.marketCap)}</div>
            <div className="text-[11px] text-zinc-500">tokenized cap</div>
          </div>
        </div>

        <dl className="mt-5 grid grid-cols-2 gap-3 text-xs">
          <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-3">
            <dt className="text-zinc-500">24h tokenized volume</dt>
            <dd className="mt-1 font-mono text-sm text-zinc-200">{money(a.volume24h)}</dd>
          </div>
          <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-3">
            <dt className="text-zinc-500">Issuer concentration</dt>
            <dd className="mt-1 font-mono text-sm text-zinc-200">
              {rwa.concentration == null ? "n/a" : `${(rwa.concentration * 100).toFixed(1)}%`}
              {top && <span className="ml-1 text-zinc-500">{top.symbol}</span>}
            </dd>
          </div>
        </dl>

        <div className="mt-4 flex flex-wrap gap-x-3 gap-y-1 text-[11px] text-zinc-500">
          <span>as of {rwa.asOf}</span>
          <span className="text-zinc-700">·</span>
          <span>{rwa.source}</span>
          <span className="text-zinc-700">·</span>
          <span className="font-mono text-zinc-600">/v5/real-world-assets/*</span>
        </div>
      </div>

      <div className="glass rounded-3xl p-6 lg:col-span-3">
        <div className="flex items-center justify-between">
          <div className="text-xs font-medium uppercase tracking-[0.16em] text-zinc-500">
            Issuer breakdown
          </div>
          <div className="text-[11px] text-zinc-500">{issuers.length} tokenized golds</div>
        </div>
        <ul className="mt-4 space-y-3">
          {issuers.map((i) => (
            <li key={`${i.symbol}-${i.issuer}`}>
              <div className="flex items-baseline justify-between gap-3 text-xs">
                <span className="flex min-w-0 items-baseline gap-2">
                  <span className="font-mono text-sm text-zinc-200">{i.symbol}</span>
                  <span className="truncate text-zinc-500">{i.issuer}</span>
                </span>
                <span className="shrink-0 font-mono text-zinc-400">
                  {money(i.marketCap)}
                  <span className="ml-2 text-zinc-600">{i.share == null ? "" : `${(i.share * 100).toFixed(1)}%`}</span>
                </span>
              </div>
              <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-white/[0.05]">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-gold to-emerald"
                  style={{ width: `${Math.max(1.5, (i.share ?? 0) * 100)}%` }}
                />
              </div>
            </li>
          ))}
        </ul>

        {rest.length > 0 && (
          <>
            <div className="mt-6 text-[10px] font-medium uppercase tracking-[0.16em] text-zinc-600">
              RWA leaderboard by 24h tokenized volume
            </div>
            <ul className="mt-2 divide-y divide-white/[0.06]">
              {rest.map((r) => (
                <li key={r.symbol} className="flex items-center justify-between gap-3 py-2 text-xs">
                  <span className="flex min-w-0 items-baseline gap-2">
                    <span className="font-mono text-zinc-300">{r.symbol}</span>
                    <span className="truncate text-zinc-500">{r.name}</span>
                    <span className="rounded bg-white/[0.04] px-1.5 py-0.5 text-[10px] text-zinc-500">
                      {r.assetType}
                    </span>
                  </span>
                  <span className="shrink-0 font-mono text-zinc-400">{money(r.volume24h)}</span>
                </li>
              ))}
            </ul>
          </>
        )}
      </div>
    </div>
  );
}
