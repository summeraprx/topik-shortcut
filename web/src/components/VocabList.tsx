"use client";

import { useMemo, useState } from "react";
import { t, type Lang } from "@/lib/i18n";
import type { Word } from "@/lib/data";

const POS: Record<string, { ko: string; en: string; th: string }> = {
  NNG: { ko: "명사", en: "noun", th: "คำนาม" },
  VV: { ko: "동사", en: "verb", th: "คำกริยา" },
  VA: { ko: "형용사", en: "adjective", th: "คำคุณศัพท์" },
  MAG: { ko: "부사", en: "adverb", th: "คำวิเศษณ์" },
  XR: { ko: "어근", en: "root", th: "รากศัพท์" },
};

export default function VocabList({ words, lang }: { words: Word[]; lang: Lang }) {
  const tr = t(lang);
  const [query, setQuery] = useState("");
  const [allRounds, setAllRounds] = useState(false);
  const [open, setOpen] = useState<string | null>(null);
  const maxRounds = Math.max(...words.map((w) => w.rounds.length));

  const shown = useMemo(
    () => words.filter((w) => (!allRounds || w.rounds.length === maxRounds) && w.lemma.includes(query.trim())),
    [words, query, allRounds, maxRounds],
  );

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-3">
        <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder={`${tr("search")}: 증가하다`}
          className="w-full rounded-lg border border-line bg-card px-3 py-2 sm:w-72" />
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={allRounds} onChange={(e) => setAllRounds(e.target.checked)} />
          {tr("sameEveryRound")}
        </label>
        <span className="text-sm text-muted">{shown.length}</span>
      </div>
      <ul className="divide-y divide-line rounded-xl border border-line bg-card">
        {shown.map((w, i) => (
          <li key={w.lemma}>
            <button onClick={() => setOpen(open === w.lemma ? null : w.lemma)} className="flex w-full items-center gap-3 px-3 py-2 text-left hover:bg-accent-soft">
              <span className="w-8 text-right text-xs tabular-nums text-muted">{i + 1}</span>
              <span className="font-medium">{w.lemma}</span>
              <span className="text-xs text-muted">{w.pos.map((p) => POS[p]?.[lang] ?? p).join(", ")}</span>
              <span className="ml-auto text-sm tabular-nums">{w.count}{tr("times")}</span>
              <span className="w-24 text-right text-xs text-muted">{w.rounds.join(" · ")}</span>
            </button>
            {open === w.lemma && (
              <ul className="space-y-1 px-14 pb-3 text-sm">
                {w.examples.map((e) => (
                  <li key={e.source}>
                    {e.sentence} <span className="text-xs text-muted">{e.source.replace("-reading-", " Q").replace("-writing-", " W")}</span>
                  </li>
                ))}
              </ul>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
