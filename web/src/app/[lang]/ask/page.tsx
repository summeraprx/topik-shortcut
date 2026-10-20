import { notFound } from "next/navigation";
import AskBox from "@/components/AskBox";
import { getGrammar } from "@/lib/data";
import { isLang, t } from "@/lib/i18n";

export default async function AskPage({ params }: PageProps<"/[lang]/ask">) {
  const { lang } = await params;
  if (!isLang(lang)) notFound();
  const tr = t(lang);
  const grammarIds = Object.fromEntries((await getGrammar()).map((g) => [g.name, g.id]));
  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-bold">{tr("navAsk")}</h1>
        <p className="mt-1 text-sm text-muted">{tr("askIntro")}</p>
      </div>
      <AskBox lang={lang} grammarIds={grammarIds} />
    </div>
  );
}
