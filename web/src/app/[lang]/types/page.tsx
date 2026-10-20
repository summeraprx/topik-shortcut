import { notFound } from "next/navigation";
import ToggleSections from "@/components/ToggleSections";
import { getOverview } from "@/lib/data";
import { isLang, pick, t } from "@/lib/i18n";

export default async function General({ params }: PageProps<"/[lang]/types">) {
  const { lang } = await params;
  if (!isLang(lang)) notFound();
  const tr = t(lang);
  const o = await getOverview();
  // official TOPIK II PBT times: period 1 = listening 60 + writing 50 min, period 2 = reading 70 min
  const parts = [["listening", o.parts.listening, 60], ["reading", o.parts.reading, 70], ["writing", o.parts.writing, 50]] as const;

  const parts2 = ["listening", "reading"] as const;
  const choices = ["1", "2", "3", "4"];
  const distribution = (
    <div className="overflow-x-auto rounded-xl border border-line bg-card">
      <table className="w-full text-center text-sm">
        <thead className="text-muted">
          <tr>
            <th rowSpan={2} className="border-b border-line p-3 text-center align-middle font-medium">{tr("round")}</th>
            {parts2.map((part) => (
              <th key={part} colSpan={4} className="border-b border-l border-line px-3 py-2 font-medium">{tr(part)}</th>
            ))}
          </tr>
          <tr className="border-b border-line">
            {parts2.map((part) =>
              choices.map((c, i) => (
                <th key={part + c} className={`px-2 py-2 font-normal ${i === 0 ? "border-l border-line" : ""}`}>{"①②③④"[i]}</th>
              )),
            )}
          </tr>
        </thead>
        <tbody>
          {o.rounds.map((r) => (
            <tr key={r} className="border-b border-line last:border-0">
              <td className="p-3 text-center font-medium">{r}</td>
              {parts2.map((part) =>
                choices.map((c, i) => (
                  <td key={part + c} className={`px-2 py-3 tabular-nums ${i === 0 ? "border-l border-line" : ""}`}>
                    {o.answer_distribution[r]?.[part]?.[c] ?? "–"}
                  </td>
                )),
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );

  const types = (
    <div className="space-y-3">
      {o.groups.map((g) => (
        <article key={`${g.section}-${g.lo}`} className="rounded-xl border border-line bg-card p-4">
          <h2 className="font-semibold">
            <span className="mr-2 rounded-md bg-accent-soft px-2 py-0.5 text-accent">
              {tr(g.section)} {g.lo === g.hi ? g.lo : `${g.lo}–${g.hi}`}
            </span>
            {pick(g.task, lang)}
          </h2>
          {!/^\d+$/.test(g.instruction) && <p className="mt-2 text-sm">{g.instruction}</p>}
          {g.words.length > 0 && (
            <div className="mt-3">
              <div className="text-xs font-medium uppercase tracking-wide text-muted">{tr("keyWords")}</div>
              <ul className="mt-1 flex flex-wrap gap-2">
                {g.words.map(([ko, en, th]) => (
                  <li key={ko} className="rounded-md bg-bg px-2 py-1 text-sm">
                    <span className="font-medium">{ko}</span> <span className="text-muted">= {lang === "th" ? th : en}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </article>
      ))}
    </div>
  );

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">{tr("navGeneral")}</h1>
      <section className="grid gap-3 sm:grid-cols-3">
        {parts.map(([key, n, minutes]) => (
          <div key={key} className="rounded-xl border border-line bg-card p-4">
            <div className="flex items-center gap-2 text-sm text-muted">
              {tr(key)}
              <span className="rounded-md border border-line px-1.5 py-0.5 text-xs">{minutes} {tr("minutes")}</span>
            </div>
            <div className="mt-1 text-2xl font-bold">{n} {tr("items")}</div>
          </div>
        ))}
      </section>
      <ToggleSections
        defaultOpen={0}
        sections={[
          { label: tr("answerSpread"), content: distribution },
          { label: tr("navTypes"), content: types },
        ]}
      />
    </div>
  );
}
