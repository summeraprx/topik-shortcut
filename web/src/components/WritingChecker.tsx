"use client";

import { useEffect, useState } from "react";
import { API, API_START, cells, get, post } from "@/lib/api";
import Wongoji from "@/components/Wongoji";
import { t, type Key, type Lang } from "@/lib/i18n";

type Prompt = { round: number; number: number; instruction: string; text: string; limits: [number, number] | null };
type Issue = { rule: string; layer: "rule" | "language" | "content" | "ai"; en: string; th: string; excerpt?: string; blank?: string };
type Result = { length: number | null; limits: [number, number] | null; issues: Issue[] };

const LAYERS: [Issue["layer"], Key][] = [["rule", "layerRule"], ["language", "layerLanguage"], ["content", "layerContent"], ["ai", "layerAI"]];

// 91 -> "91ˢᵗ", 102 -> "102ⁿᵈ" (superscript letters: <option> cannot hold styled text)
const SUP: Record<string, string> = { st: "ˢᵗ", nd: "ⁿᵈ", rd: "ʳᵈ", th: "ᵗʰ" };
function ordinal(n: number) {
  const s = n % 100 >= 11 && n % 100 <= 13 ? "th" : ({ 1: "st", 2: "nd", 3: "rd" } as Record<number, string>)[n % 10] ?? "th";
  return `${n}${SUP[s]}`;
}

// 53/54 have no ※ line: their command is the start of the question text, up to "(30점)" / "(50점)"
function command(p: Prompt) {
  if (p.instruction) return p.instruction;
  const m = p.text.match(/^[\s\S]*?\(\d+점\)/);
  return m ? `${p.number}. ${m[0].replace(/\s+/g, " ")}` : "";
}

export default function WritingChecker({ lang }: { lang: Lang }) {
  const tr = t(lang);
  const [prompts, setPrompts] = useState<Prompt[] | null>(null);
  const [down, setDown] = useState(false);
  const [pick, setPick] = useState("102-53");
  const [essay, setEssay] = useState("");
  const [blanks, setBlanks] = useState({ "㉠": "", "㉡": "" });
  const [useAI, setUseAI] = useState(false);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<Result | null>(null);

  useEffect(() => {
    get<Prompt[]>("/writing/prompts").then(setPrompts).catch(() => setDown(true));
  }, []);

  const [round, number] = pick.split("-").map(Number);
  const prompt = prompts?.find((p) => p.round === round && p.number === number);
  const essayMode = number >= 53;
  const length = cells(essay);
  const [lo, hi] = prompt?.limits ?? [0, 0];
  // the answer can be checked only when it meets the requirement
  const ready = essayMode ? length >= lo && length <= hi : blanks["㉠"].trim() !== "" && blanks["㉡"].trim() !== "";

  async function check() {
    setBusy(true); setResult(null);
    try {
      setResult(await post<Result>("/writing/check", { round, number, answer: essayMode ? essay : blanks, ai: useAI }));
    } catch {
      setDown(true);
    } finally {
      setBusy(false);
    }
  }

  if (down) {
    return <p className="rounded-lg bg-warn-soft p-3 text-sm text-warn">{tr("apiDown")} <code className="block pt-1">{API_START}</code></p>;
  }
  if (!prompts) return <p className="animate-pulse text-sm text-muted">…</p>;

  return (
    <div className="space-y-4">
      <label className="flex flex-wrap items-center gap-2 text-sm">
        {tr("pickQuestion")}
        <select value={pick} onChange={(e) => { setPick(e.target.value); setResult(null); }}
          className="rounded-lg border border-line bg-card px-2 py-1">
          {prompts.map((p) => (
            <option key={`${p.round}-${p.number}`} value={`${p.round}-${p.number}`}>
              {ordinal(p.round)} TOPIK II - Q.{p.number}
            </option>
          ))}
        </select>
      </label>

      {prompt && (
        <div className="rounded-xl border border-line bg-card p-4 text-sm">
          <p className="mb-3 font-medium">{command(prompt)}</p>
          {/* the whole question as printed, with its graph or picture */}
          {/* eslint-disable-next-line @next/next/no-img-element -- served by the local API, not a static asset */}
          <img src={`${API}/writing/image/${round}/${number}`} alt={`${round} Q${number}`} className="w-full rounded-md bg-white" />
        </div>
      )}

      <div className="space-y-2">
        <div className="text-sm font-medium">{tr("yourAnswer")}</div>
        {essayMode ? (
          <>
            <Wongoji value={essay} onChange={setEssay} minRows={Math.ceil(hi / 25)} />
            <div className={`text-sm tabular-nums ${length && (length < lo || length > hi) ? "text-bad" : "text-ok"}`}>
              {length} / {lo}–{hi} {tr("characters")}
            </div>
          </>
        ) : (
          (["㉠", "㉡"] as const).map((m) => (
            <label key={m} className="flex items-center gap-2">
              <span className="w-6 text-lg">{m}</span>
              <input value={blanks[m]} onChange={(e) => setBlanks({ ...blanks, [m]: e.target.value })}
                className="flex-1 rounded-lg border border-line bg-card px-3 py-2" />
            </label>
          ))
        )}
      </div>

      <div className="flex flex-wrap items-center gap-4">
        <button onClick={check} disabled={busy || !ready} className="rounded-lg bg-accent px-4 py-2 text-white disabled:opacity-50">
          {busy ? tr("checking") : tr("check")}
        </button>
        {!ready && <span className="text-sm text-muted">{tr(essayMode ? "needLength" : "needBlanks")}</span>}
        {essayMode && (
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={useAI} onChange={(e) => setUseAI(e.target.checked)} />
            {tr("useAI")}
          </label>
        )}
      </div>

      {result && (
        <div className="space-y-3">
          {result.issues.length === 0 && <p className="rounded-lg bg-card p-3 text-ok">✓ {tr("noIssues")}</p>}
          {lang === "ko" && result.issues.length > 0 && <p className="text-xs text-muted">{tr("feedbackLang")}</p>}
          {LAYERS.map(([layer, key]) => {
            const found = result.issues.filter((i) => i.layer === layer);
            if (!found.length) return null;
            return (
              <section key={layer} className="rounded-xl border border-line bg-card p-4">
                <h2 className="mb-2 font-semibold">{tr(key)} ({found.length})</h2>
                <ul className="space-y-2 text-sm">
                  {found.map((i, n) => (
                    <li key={n} className="flex gap-2">
                      <span className={layer === "ai" ? "text-warn" : "text-bad"}>•</span>
                      <span>
                        {i.blank && <b className="mr-1">{i.blank}</b>}
                        {lang === "th" ? i.th : i.en}
                        {i.excerpt && layer !== "ai" && <span className="ml-2 rounded bg-bg px-1 text-xs text-muted">{i.excerpt}</span>}
                      </span>
                    </li>
                  ))}
                </ul>
              </section>
            );
          })}
        </div>
      )}
    </div>
  );
}
