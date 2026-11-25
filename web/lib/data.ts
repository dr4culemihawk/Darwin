import darwin from "@/public/data/darwin.json";

/* ---- Types (shape of web/public/data/darwin.json) ---- */

export interface Indicator {
  id: string;
  type: string;
  period?: number;
  source?: string;
  fast?: number;
  slow?: number;
  signal?: number;
}

export interface Condition {
  left: string;
  op: string;
  right: string | number;
}

export interface Champion {
  name: string;
  fingerprint: string;
  rationale: string;
  universe: string[];
  timeframe: string;
  indicators: Indicator[];
  entry: { all?: Condition[]; any?: Condition[] };
  exit: { all?: Condition[]; any?: Condition[] };
  risk: Record<string, number>;
  sizing: { type: string; fraction: number };
}

export interface Metrics {
  totalReturn: number;
  cagr: number;
  sharpe: number;
  sortino: number;
  maxDrawdown: number;
  calmar: number;
  winRate: number;
  numTrades: number;
  exposure: number;
  ruleAdherence: number;
  finalEquity: number;
}

export interface EquityPoint {
  date: string;
  value: number;
}

export interface Generation {
  generation: number;
  best_fitness: number;
  mean_fitness: number;
  best: string;
}

export interface FearGreed {
  value: number | null;
  classification: string;
  series: { date: string; value: number }[];
  source: string;
}

export interface Identity {
  agentId: number | null;
  txHash: string;
  registry: string;
  wallet: string;
  network: string;
  gasless: boolean;
  explorer: string;
}

export interface Meta {
  dataSource: string;
  universe: string[];
  bars: number;
  generations: number;
  oosStart?: string;
  provenance?: {
    symbols: Record<string, string>;
    notes: Record<string, string>;
    regime: Record<string, string>;
  };
  sponsors: { cmc: string; bnb: string; twak: string };
}

/* ---- New for Build with CMC Round 2 ---- */

export interface RegimeComponent {
  name: string;
  value: number | null;
  reading: string;
  endpoint: string;
  format: "num" | "pct" | "pp" | "usd";
  digits: number;
  source: string;
}

export interface RegimeHistoryPoint {
  date: string;
  btcDominance: number | null;
  goldRs: number | null;
}

export interface RegimeMetricSet {
  btcDominance: number | null;
  domChange30d: number | null;
  ethDominance: number | null;
  totalMarketCap: number | null;
  marketCapChange30d: number | null;
  cmc100: number | null;
  cmc100Change24h: number | null;
  goldPrice: number | null;
  goldChange30d: number | null;
  goldRs: number | null;
  goldMarketCap?: number | null;
  goldVolume24h?: number | null;
}

export interface Regime {
  asOf: string | null;
  source: string;
  label: string;
  tone: "risk-on" | "risk-off" | "neutral";
  note: string;
  metrics: RegimeMetricSet;
  history: RegimeHistoryPoint[];
  components: RegimeComponent[];
  provenance: Record<string, string>;
}

export interface RwaIssuer {
  symbol: string;
  name: string;
  issuer: string;
  price: number | null;
  marketCap: number | null;
  volume24h: number | null;
  share: number | null;
}

export interface RwaLeaderboardRow {
  name: string;
  symbol: string;
  assetType: string;
  marketCap: number | null;
  volume24h: number | null;
  price: number | null;
}

export interface Rwa {
  source: string;
  asOf: string;
  asset: {
    symbol: string;
    name: string;
    assetType: string;
    price: number | null;
    marketCap: number | null;
    volume24h: number | null;
    change30d: number | null;
  };
  issuers: RwaIssuer[];
  concentration: number | null;
  leaderboard: RwaLeaderboardRow[];
}

export interface SignalLeaf {
  text: string;
  left: string;
  op: string;
  right: string;
  leftValue: number | null;
  rightValue: number | null;
  result: boolean | null;
}

export interface SymbolSignal {
  symbol: string;
  action: "enter" | "exit" | "flat" | "unknown" | "no_data";
  reason?: string;
  asOf: string | null;
  lastClose?: number;
  entry: SignalLeaf[];
  exit: SignalLeaf[];
}

export interface TodaySignal {
  champion: string;
  fingerprint: string;
  asOf: string | null;
  signalSources: string[];
  actions: SymbolSignal[];
  summary: string;
}


export interface OOS {
  splitDate: string;
  inSample: Metrics;
  outOfSample: Metrics;
}

export interface DarwinData {
  champion: Champion;
  metrics: Metrics;
  equity: EquityPoint[];
  oos?: OOS;
  history: Generation[];
  fearGreed: FearGreed;
  identity: Identity;
  meta: Meta;
  /* New for Round 2 — optional so an older data file still renders. */
  regime?: Regime;
  rwa?: Rwa;
  todaySignal?: TodaySignal;
}

export const data = darwin as DarwinData;

/* ---- Derived helpers ---- */

/** The raw GA name is a long crossover concatenation; produce a clean human title. */
export function championTitle(name: string): string {
  // Collapse repeated lineage fragments into a readable hybrid name.
  const parts = name
    .split(/\s+x\s+/i)
    .map((p) => p.replace(/#\d+/g, "").trim())
    .filter(Boolean);
  const seen = new Set<string>();
  const unique: string[] = [];
  for (const p of parts) {
    const key = p.toLowerCase();
    if (!seen.has(key)) {
      seen.add(key);
      unique.push(p);
    }
  }
  const top = unique.slice(0, 2);
  return top.join(" × ");
}

export function pct(n: number, digits = 1): string {
  return `${n >= 0 ? "+" : ""}${(n * 100).toFixed(digits)}%`;
}

export function pctAbs(n: number, digits = 1): string {
  return `${(n * 100).toFixed(digits)}%`;
}

export function num(n: number, digits = 2): string {
  return n.toFixed(digits);
}

export function usd(n: number): string {
  return n.toLocaleString("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });
}

export function shortAddr(a: string, head = 6, tail = 4): string {
  if (!a) return "";
  return a.length > head + tail ? `${a.slice(0, head)}…${a.slice(-tail)}` : a;
}
