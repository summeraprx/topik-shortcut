import { notFound } from "next/navigation";
import GrammarList from "@/components/GrammarList";
import { getGrammar } from "@/lib/data";
import { isLang, t } from "@/lib/i18n";

export default async function GrammarPage({ params }: PageProps<"/[lang]/grammar">) {
  const { lang } = await params;
  if (!isLang(lang)) notFound();
  const tr = t(lang);
  const grammar = await getGrammar();
  // send only what the list needs to the browser
  const items = grammar.map(({ id, name, meaning, count, rounds, in_q1_4 }) => ({ id, name, meaning, count, rounds, in_q1_4 }));
  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-bold">{tr("navGrammar")}</h1>
        <p className="mt-1 text-sm text-muted">{tr("shortcut3Body")}</p>
      </div>
      <GrammarList items={items} lang={lang} />
    </div>
  );
}
