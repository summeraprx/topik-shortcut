"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { pick, t, type Lang } from "@/lib/i18n";
import type { Grammar } from "@/lib/data";

type Item = Pick<Grammar, "id" | "name" | "meaning" | "count" | "rounds" | "in_q1_4">;

export default function GrammarList({ items, lang }: { items: Item[]; lang: Lang }) {
  const tr = t(lang);
  const [query, setQuery] = useState("");
  const [onlyQ14, setOnlyQ14] = useState(false);

  const shown = useMemo(() => {
    const q = query.trim().toLowerCase();
    return items
      .filter((g) => !onlyQ14 || g.in_q1_4.length > 0)
      .filter((g) => !q || g.name.includes(q) || pick(g.meaning, lang).toLowerCase().includes(q) || g.meaning.en.toLowerCase().includes(q))
      .sort((a, b) => b.count - a.count);
  }, [items, query, onlyQ14, lang]);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={`${tr("search")}: -는 바람에, because…`}
          className="w-full rounded-lg border border-line bg-card px-3 py-2 sm:w-80"
        />
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={onlyQ14} onChange={(e) => setOnlyQ14(e.target.checked)} />
          {tr("onlyQ14")}
        </label>
        <span className="text-sm text-muted">{shown.length}</span>
      </div>
      <ul className="grid gap-2 sm:grid-cols-2">
        {shown.map((g) => (
          <li key={g.id}>
            <Link href={`/${lang}/grammar/${g.id}`} className="flex h-full items-start justify-between gap-3 rounded-xl border border-line bg-card p-3 hover:border-accent">
              <div>
                <div className="font-semibold">{g.name}</div>
                <div className="text-sm text-muted">{pick(g.meaning, lang)}</div>
              </div>
              <div className="shrink-0 text-right text-xs">
                <div className="tabular-nums">{g.count}{tr("times")}</div>
                {g.in_q1_4.length > 0 && <div className="mt-1 rounded bg-warn-soft px-1.5 py-0.5 text-warn">{tr("inQ14")}</div>}
              </div>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
