import Link from "next/link";
import { getOverview } from "@/lib/data";
import { isLang, pick, t, type Lang } from "@/lib/i18n";
import { notFound } from "next/navigation";

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-xl border border-line bg-card p-4">
      <div className="text-2xl font-bold">{value}</div>
      <div className="text-sm text-muted">{label}</div>
    </div>
  );
}

function Shortcut({ title, body, href, lang }: { title: string; body: string; href: string; lang: Lang }) {
  return (
    <Link href={`/${lang}/${href}`} className="block rounded-xl border border-line bg-card p-4 hover:border-accent">
      <div className="font-semibold">{title}</div>
      <p className="mt-1 text-sm text-muted">{body}</p>
    </Link>
  );
}

export default async function Home({ params }: PageProps<"/[lang]">) {
  const { lang } = await params;
  if (!isLang(lang)) notFound();
  const tr = t(lang);
  const o = await getOverview();
  const sections: [string, "listening" | "reading"][] = [["listening", "listening"], ["reading", "reading"]];

  return (
    <div className="space-y-8">
      <section>
        <h1 className="text-2xl font-bold sm:text-3xl">{tr("appName")}</h1>
        <p className="mt-1 text-muted">{tr("tagline")}</p>
      </section>

      <section className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Stat label={tr("rounds")} value={o.rounds.join(" · ")} />
        <Stat label={tr("questions")} value={o.counts.questions} />
        <Stat label={tr("words")} value={o.counts.words.toLocaleString()} />
        <Stat label={tr("grammarPoints")} value={o.counts.grammar} />
      </section>

      <section className="grid gap-3 sm:grid-cols-3">
        <Shortcut lang={lang} href="types" title={tr("shortcut1Title")} body={tr("shortcut1Body")} />
        <Shortcut lang={lang} href="grammar" title={tr("shortcut3Title")} body={tr("shortcut3Body")} />
        <Shortcut lang={lang} href="" title={tr("shortcut2Title")} body={tr("shortcut2Body")} />
      </section>

      <section>
        <h2 className="mb-3 text-lg font-semibold">{tr("answerSpread")}</h2>
        <div className="overflow-x-auto rounded-xl border border-line bg-card">
          <table className="w-full text-sm">
            <thead className="text-muted">
              <tr className="border-b border-line">
                <th className="p-3 text-left font-medium">{tr("round")}</th>
                {sections.map(([s, key]) => (
                  <th key={s} className="p-3 text-left font-medium">{tr(key)} ①②③④</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {o.rounds.map((r) => (
                <tr key={r} className="border-b border-line last:border-0">
                  <td className="p-3 font-medium">{r}</td>
                  {sections.map(([s]) => (
                    <td key={s} className="p-3 tabular-nums">
                      {Object.values(o.answer_distribution[r]?.[s] ?? {}).join(" · ")}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section>
        <h2 className="mb-3 text-lg font-semibold">{tr("navTypes")}</h2>
        <div className="flex flex-wrap gap-2">
          {o.question_types.map((q) => (
            <Link key={q.instruction} href={`/${lang}/types`} className="rounded-full border border-line bg-card px-3 py-1 text-sm hover:border-accent">
              <span className="font-semibold">{q.section === "writing" ? "W" : "Q"}{q.numbers.length > 3 ? `${q.numbers[0]}…` : q.numbers.join(",")}</span>{" "}
              <span className="text-muted">{pick(q.task, lang)}</span>
            </Link>
          ))}
        </div>
      </section>
    </div>
  );
}
