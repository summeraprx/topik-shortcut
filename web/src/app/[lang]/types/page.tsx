import { notFound } from "next/navigation";
import { getOverview } from "@/lib/data";
import { isLang, pick, t } from "@/lib/i18n";

// Turn [1,2,16,17,18] into "1–2, 16–18"
function ranges(nums: number[]) {
  const out: string[] = [];
  let start = nums[0];
  for (let i = 1; i <= nums.length; i++) {
    if (nums[i] !== nums[i - 1] + 1) {
      out.push(start === nums[i - 1] ? `${start}` : `${start}–${nums[i - 1]}`);
      start = nums[i];
    }
  }
  return out.join(", ");
}

export default async function Types({ params }: PageProps<"/[lang]/types">) {
  const { lang } = await params;
  if (!isLang(lang)) notFound();
  const tr = t(lang);
  const { question_types } = await getOverview();

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-bold">{tr("navTypes")}</h1>
        <p className="mt-1 text-sm text-muted">{tr("shortcut1Body")}</p>
      </div>
      {question_types.map((q) => (
        <article key={q.instruction} className="rounded-xl border border-line bg-card p-4">
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <h2 className="font-semibold">
              <span className="mr-2 rounded-md bg-accent-soft px-2 py-0.5 text-accent">
                {q.section === "writing" ? tr("writing") : tr("reading")} {ranges(q.numbers)}
              </span>
              {pick(q.task, lang)}
            </h2>
            {q.same_in_all_rounds && <span className="text-xs text-ok">✓ {tr("sameEveryRound")}</span>}
          </div>
          {!/^\d+$/.test(q.instruction) && <p className="mt-2 text-sm">{q.instruction}</p>}
          {q.words.length > 0 && (
            <div className="mt-3">
              <div className="text-xs font-medium uppercase tracking-wide text-muted">{tr("keyWords")}</div>
              <ul className="mt-1 flex flex-wrap gap-2">
                {q.words.map(([ko, en, th]) => (
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
}
