"use client";

import Link from "next/link";
import { Fragment, useState } from "react";
import { API_START, post } from "@/lib/api";
import { t, type Lang } from "@/lib/i18n";

type Source = { id: string; kind: "question" | "grammar"; text: string };
type Answer = { answer: string; sources: Source[]; invalid_citations: string[]; seconds: number };

const CITE = /\[([^\[\]]+)\]/g;

function label(id: string) {
  if (id.startsWith("grammar:")) return id.slice(8);
  const [round, section, number] = id.split("-");
  return `${round} ${section === "writing" ? "W" : "Q"}${number}`;
}

export default function AskBox({ lang, grammarIds }: { lang: Lang; grammarIds: Record<string, number> }) {
  const tr = t(lang);
  const [question, setQuestion] = useState("");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<Answer | null>(null);
  const [error, setError] = useState(false);

  async function ask(e: React.FormEvent) {
    e.preventDefault();
    if (question.trim().length < 2 || busy) return;
    setBusy(true); setError(false); setResult(null);
    try {
      setResult(await post<Answer>("/ask", { question }));
    } catch {
      setError(true);
    } finally {
      setBusy(false);
    }
  }

  // "[96-reading-3]" in the answer -> a small link to the source card below (or to the grammar page)
  function render(text: string) {
    const parts = text.split(CITE);
    return parts.map((p, i) => {
      if (i % 2 === 0) return <Fragment key={i}>{p}</Fragment>;
      return p.split(/[,;]/).map((id) => id.trim()).filter(Boolean).map((id) => {
        const gid = id.startsWith("grammar:") ? grammarIds[id.slice(8)] : undefined;
        const cls = "mx-0.5 rounded bg-accent-soft px-1 text-xs text-accent";
        return gid !== undefined
          ? <Link key={i + id} href={`/${lang}/grammar/${gid}`} className={cls}>{label(id)}</Link>
          : <a key={i + id} href={`#src-${id}`} className={cls}>{label(id)}</a>;
      });
    });
  }

  return (
    <div className="space-y-4">
      <form onSubmit={ask} className="flex flex-col gap-2 sm:flex-row">
        <input value={question} onChange={(e) => setQuestion(e.target.value)} placeholder={tr("askPlaceholder")}
          className="flex-1 rounded-lg border border-line bg-card px-3 py-2" />
        <button disabled={busy} className="rounded-lg bg-accent px-4 py-2 text-white disabled:opacity-50">{tr("askButton")}</button>
      </form>
      {busy && <p className="animate-pulse text-sm text-muted">{tr("asking")}</p>}
      {error && (
        <p className="rounded-lg bg-warn-soft p-3 text-sm text-warn">
          {tr("apiDown")} <code className="block pt-1">{API_START}</code>
        </p>
      )}
      {result && (
        <div className="space-y-4">
          <div className="whitespace-pre-line rounded-xl border border-line bg-card p-4 leading-relaxed">{render(result.answer)}</div>
          <p className="text-xs text-muted">{result.seconds}s{result.invalid_citations.length > 0 && ` · ⚠ ${result.invalid_citations.join(", ")}`}</p>
          <div>
            <h2 className="mb-2 text-sm font-semibold text-muted">{tr("sources")}</h2>
            <ul className="grid gap-2 sm:grid-cols-2">
              {result.sources.map((s) => (
                <li key={s.id} id={`src-${s.id}`} className="rounded-lg border border-line bg-card p-3 text-sm">
                  <div className="mb-1 font-semibold">{label(s.id)}</div>
                  <p className="line-clamp-4 whitespace-pre-line text-muted">{s.text}</p>
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}
