import Link from "next/link";
import { notFound } from "next/navigation";
import { getGrammar } from "@/lib/data";
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

// "ปรากฏ 95 ครั้ง (TOPIK II PBT ครั้งที่ 91, 96, 102)"
function appears(lang: string, count: number, rounds: number[]) {
  const r = rounds.join(", ");
  if (lang === "th") return `ปรากฏ ${count} ครั้ง (TOPIK II PBT ครั้งที่ ${r})`;
  if (lang === "ko") return `${count}회 출제 (TOPIK II PBT 제${rounds.join("·")}회)`;
  return `Appears ${count} times (TOPIK II PBT rounds ${r})`;
}

// "ออกสอบในพาร์ทอ่าน ข้อ 1–4: ครั้งที่ 102: Q4, ครั้งที่ 91: Q1"
function inQ14(lang: string, ids: string[]) {
  const refs = ids.map((id) => {
    const [round, , q] = id.split("-");
    return lang === "th" ? `ครั้งที่ ${round}: Q${q}` : lang === "ko" ? `제${round}회: ${q}번` : `round ${round}: Q${q}`;
  });
  const head = lang === "th" ? "ออกสอบในพาร์ทอ่าน ข้อ 1–4" : lang === "ko" ? "읽기 1~4번 출제" : "In Reading Q1–4";
  return `${head}: ${refs.join(", ")}`;
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
        <p className="mt-2 text-sm text-muted">{appears(lang, g.count, g.rounds)}</p>
        {g.in_q1_4.length > 0 && (
          <p className="mt-2 inline-block rounded bg-warn-soft px-2 py-1 text-sm text-warn">{inQ14(lang, g.in_q1_4)}</p>
        )}
      </header>

      {g.form[textLang] && (
        <Section title={tr("form")}>
          <ul className="space-y-1">
            {g.form[textLang]!.split(/\s*·\s*|\n/).filter(Boolean).map((use) => <li key={use}>{use}</li>)}
          </ul>
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
          {g.note[textLang] && (
            <div className="mt-3 rounded-lg bg-bg p-3 text-sm">
              <div className="mb-1 font-semibold">{tr("memoryTip")}</div>
              <p className="whitespace-pre-line">{g.note[textLang]}</p>
            </div>
          )}
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
