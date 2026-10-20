import Link from "next/link";
import { notFound } from "next/navigation";
import Examples from "@/components/Examples";
import { getGrammar, sourceLabel } from "@/lib/data";
import { isLang, pick, t } from "@/lib/i18n";

export async function generateStaticParams() {
  const grammar = await getGrammar();
  return grammar.map((g) => ({ id: String(g.id) }));
}

const RULE_MARK = { ok: "✓", no: "✗", note: "•" } as const;
const RULE_COLOR = { ok: "text-ok", no: "text-bad", note: "text-muted" } as const;

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="border-t border-line pt-4">
      <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted">{title}</h2>
      {children}
    </section>
  );
}

export default async function GrammarDetail({ params }: PageProps<"/[lang]/grammar/[id]">) {
  const { lang, id } = await params;
  if (!isLang(lang)) notFound();
  const tr = t(lang);
  const all = await getGrammar();
  const g = all.find((x) => String(x.id) === id);
  if (!g) notFound();
  const byName = new Map(all.map((x) => [x.name, x.id]));
  const textLang = lang === "th" ? "th" : "en"; // content exists in EN and TH; Korean shows English for now

  return (
    <article className="space-y-5 rounded-2xl border border-line bg-card p-5">
      <Link href={`/${lang}/grammar`} className="text-sm text-muted hover:text-accent">{tr("back")}</Link>
      <header>
        <h1 className="text-3xl font-bold">{g.name}</h1>
        <p className="mt-1 text-lg">{pick(g.meaning, lang)}</p>
        <p className="mt-2 text-sm text-muted">
          {g.count}{tr("times")} · {tr("round")} {g.rounds.join(", ")}
          {g.in_q1_4.length > 0 && (
            <span className="ml-2 rounded bg-warn-soft px-1.5 py-0.5 text-warn">
              {tr("inQ14")}: {g.in_q1_4.map(sourceLabel).join(", ")}
            </span>
          )}
        </p>
      </header>

      {g.form[textLang] && (
        <Section title={tr("form")}>
          <p className="whitespace-pre-line">{g.form[textLang]}</p>
        </Section>
      )}

      {g.rules.length > 0 && (
        <Section title={tr("rules")}>
          <ul className="space-y-1">
            {g.rules.map((r, i) => (
              <li key={i} className="flex gap-2">
                <span className={RULE_COLOR[r.t]}>{RULE_MARK[r.t]}</span>
                <span>{r[textLang]}</span>
              </li>
            ))}
          </ul>
        </Section>
      )}

      {g.similar.length > 0 && (
        <Section title={tr("similar")}>
          <ul className="flex flex-wrap gap-2">
            {g.similar.map((s) => {
              const sid = byName.get(s.g);
              return (
                <li key={s.g}>
                  {sid !== undefined ? (
                    <Link href={`/${lang}/grammar/${sid}`} className="rounded-md border border-line px-2 py-1 hover:border-accent">≈ {s.g}</Link>
                  ) : (
                    <span className="rounded-md border border-line px-2 py-1">≈ {s.g}</span>
                  )}
                </li>
              );
            })}
          </ul>
          {g.note[textLang] && <p className="mt-3 whitespace-pre-line rounded-lg bg-bg p-3 text-sm">{g.note[textLang]}</p>}
        </Section>
      )}

      {g.examples.length > 0 && (
        <Section title={`${tr("sameGrammar")} (${g.examples.length})`}>
          <Examples items={g.examples.map((e) => ({ ...e, source: sourceLabel(e.source) }))} showAllLabel={tr("showAll")} />
        </Section>
      )}

      {g.similar.filter((s) => s.exam).map((s) => {
        const [, rnd, q] = s.exam!.match(/round (\d+) Q(\d+)/) ?? [];
        const text =
          lang === "th" ? `${g.name} ≈ ${s.g} (เคยออกข้อสอบครั้งที่ ${rnd} ข้อ ${q})`
          : lang === "ko" ? `${g.name} ≈ ${s.g} (제${rnd}회 ${q}번 기출)`
          : `${g.name} ≈ ${s.g} (appeared in the exam: round ${rnd} Q${q})`;
        return <p key={s.g} className="rounded-lg bg-warn-soft p-3 text-sm text-warn">{text}</p>;
      })}
    </article>
  );
}
