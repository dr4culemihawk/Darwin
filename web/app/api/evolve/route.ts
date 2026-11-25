import Anthropic from "@anthropic-ai/sdk";
import { NextResponse } from "next/server";
import { data } from "@/lib/data";
import { SYSTEM, mutatePrompt, extractJson, validateSpec } from "@/lib/llm";

// Calls Claude → must run on the Node runtime, not edge.
export const runtime = "nodejs";
export const dynamic = "force-dynamic";

// Mirror the offline engine: model + optional Anthropic-compatible gateway base URL.
const MODEL = process.env.DARWIN_MODEL || "claude-opus-5-5";
const BASE_URL = process.env.ANTHROPIC_BASE_URL || undefined;
// Server-side refusal fallbacks are a first-party API feature, only on these models.
const SUPPORTS_FALLBACK = !BASE_URL && /^claude-(opus-5|fable-5|sonnet-5-5)/.test(MODEL);

// Best-effort guard so a public endpoint can't be hammered into burning your key.
// (Serverless is multi-instance, so this is a soft limit per warm instance.)
const HITS = new Map<string, number[]>();
const WINDOW_MS = 60_000;
const MAX_PER_WINDOW = 6;

function rateLimited(ip: string): boolean {
  const now = Date.now();
  const recent = (HITS.get(ip) || []).filter((t) => now - t < WINDOW_MS);
  recent.push(now);
  HITS.set(ip, recent);
  return recent.length > MAX_PER_WINDOW;
}

export async function POST(req: Request) {
  const key = process.env.ANTHROPIC_API_KEY;
  if (!key) {
    return NextResponse.json(
      { error: "Live evolution is offline — no ANTHROPIC_API_KEY configured on the server." },
      { status: 503 },
    );
  }

  const ip = req.headers.get("x-forwarded-for")?.split(",")[0]?.trim() || "local";
  if (rateLimited(ip)) {
    return NextResponse.json(
      { error: "Slow down — too many live evolutions. Try again in a moment." },
      { status: 429 },
    );
  }

  try {
    const client = new Anthropic({ apiKey: key, baseURL: BASE_URL });
    const prompt = mutatePrompt(data.champion, data.metrics, data.fearGreed.value);

    // Current models always think. Low effort keeps the live demo snappy; the
    // token cap leaves room for thinking plus the JSON spec.
    const params = {
      model: MODEL,
      max_tokens: 8000,
      output_config: { effort: "low" as const },
      system: SYSTEM,
      messages: [{ role: "user" as const, content: prompt }],
    };
    const msg = SUPPORTS_FALLBACK
      ? await client.beta.messages.create({
          ...params,
          betas: ["server-side-fallback-2026-06-01"],
          fallbacks: [{ model: "claude-opus-4-8" }],
        })
      : await client.messages.create(params);

    if (msg.stop_reason === "refusal") {
      return NextResponse.json({ error: "The model declined this request. Try again." }, { status: 502 });
    }
    if (msg.stop_reason === "max_tokens") {
      return NextResponse.json(
        { error: "The model ran out of output room before finishing the spec. Try again." },
        { status: 502 },
      );
    }

    const text = msg.content
      .flatMap((b) => (b.type === "text" ? [b.text] : []))
      .join("");

    const spec = validateSpec(extractJson(text));
    return NextResponse.json({ spec, model: msg.model });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Live evolution failed.";
    // Surface a clean, user-facing reason; never leak the key or stack.
    return NextResponse.json({ error: message }, { status: 502 });
  }
}
