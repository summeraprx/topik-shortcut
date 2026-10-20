"use client";

import { useMemo, useState } from "react";
import { pick, t, type Lang } from "@/lib/i18n";
import type { Word } from "@/lib/data";

const POS: Record<string, { ko: string; en: string; th: string; abbr: string }> = {
  NNG: { ko: "명사", en: "noun", th: "คำนาม", abbr: "n." },
  VV: { ko: "동사", en: "verb", th: "คำกริยา", abbr: "v." },
  VA: { ko: "형용사", en: "adjective", th: "คำคุณศัพท์", abbr: "adj." },
  MAG: { ko: "부사", en: "adverb", th: "คำวิเศษณ์", abbr: "adv." },
  XR: { ko: "어근", en: "root", th: "รากศัพท์", abbr: "root" },
};

// Cards like the grammar list: word + meaning on one line, part of speech, frequency (small). Not clickable.
// Part-of-speech filter: nothing checked = all words; otherwise words with any checked part of speech.
export default function VocabList({ words, lang }: { words: Word[]; lang: Lang }) {
  const tr = t(lang);
  const [query, setQuery] = useState("");
  const [pos, setPos] = useState<string[]>([]);

  const counts = useMemo(() => {
    const c: Record<string, number> = {};
    for (const w of words) for (const p of w.pos) c[p] = (c[p] ?? 0) + 1;
    return c;
  }, [words]);

  const shown = useMemo(() => {
    const q = query.trim().toLowerCase();
    return words
      .filter((w) => pos.length === 0 || w.pos.some((p) => pos.includes(p)))
      .filter((w) => !q || w.lemma.includes(q) || pick(w.meaning, lang).toLowerCase().includes(q) || w.meaning.en.toLowerCase().includes(q));
  }, [words, query, pos, lang]);

  function toggle(p: string) {
    setPos(pos.includes(p) ? pos.filter((x) => x !== p) : [...pos, p]);
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder={`${tr("search")}: 증가하다, increase…`}
          className="w-full rounded-lg border border-line bg-card px-3 py-2 sm:w-80" />
        <span className="text-sm text-muted">{shown.length}</span>
      </div>
      <fieldset className="flex flex-wrap items-center gap-x-4 gap-y-2 text-sm">
        <legend className="sr-only">{tr("partOfSpeech")}</legend>
        {Object.keys(POS).filter((p) => counts[p]).map((p) => (
          <label key={p} className="flex items-center gap-1.5">
            <input type="checkbox" checked={pos.includes(p)} onChange={() => toggle(p)} />
            {POS[p][lang]} ({POS[p].abbr}) <span className="text-xs text-muted">{counts[p]}</span>
          </label>
        ))}
      </fieldset>
      <ul className="grid gap-2 sm:grid-cols-2">
        {shown.map((w) => (
          <li key={w.lemma} className="flex h-full items-start justify-between gap-3 rounded-xl border border-line bg-card p-3">
            <div>
              <div>
                <span className="font-semibold">{w.lemma}</span>
                <span className="ml-2 text-sm text-muted">{pick(w.meaning, lang)}</span>
              </div>
              <div className="mt-1 text-xs text-muted">{w.pos.map((p) => `${POS[p]?.[lang] ?? p} (${POS[p]?.abbr ?? ""})`).join(", ")}</div>
            </div>
            <div className="shrink-0 text-xs tabular-nums text-muted">{w.count}{tr("times")}</div>
          </li>
        ))}
      </ul>
    </div>
  );
}
