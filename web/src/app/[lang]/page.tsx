import Link from "next/link";
import { getOverview } from "@/lib/data";
import { isLang, t } from "@/lib/i18n";
import { notFound } from "next/navigation";

function Stat({ label, value, href }: { label: string; value: string | number; href?: string }) {
  const body = (
    <>
      <div className="text-sm text-muted">{label}</div>
      <div className="mt-1 text-2xl font-bold">{value}</div>
    </>
  );
  return href ? (
    <Link href={href} className="block rounded-xl border border-line bg-card p-4 hover:border-accent">{body}</Link>
  ) : (
    <div className="rounded-xl border border-line bg-card p-4">{body}</div>
  );
}

export default async function Home({ params }: PageProps<"/[lang]">) {
  const { lang } = await params;
  if (!isLang(lang)) notFound();
  const tr = t(lang);
  const o = await getOverview();

  return (
    <div className="space-y-8">
      <section>
        <h1 className="text-2xl font-bold sm:text-3xl">{tr("appName")}</h1>
        <p className="mt-1 text-muted">{tr("tagline")}</p>
      </section>

      <section className="grid gap-3 sm:grid-cols-3">
        <Stat label={tr("rounds")} value={o.rounds.join(" · ")} />
        <Stat label={tr("words")} value={o.counts.words.toLocaleString()} href={`/${lang}/vocab`} />
        <Stat label={tr("grammarPoints")} value={o.counts.grammar} href={`/${lang}/grammar`} />
      </section>
    </div>
  );
}
