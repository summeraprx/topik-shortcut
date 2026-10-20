import { notFound } from "next/navigation";
import VocabList from "@/components/VocabList";
import { getVocab } from "@/lib/data";
import { isLang, t } from "@/lib/i18n";

export default async function VocabPage({ params }: PageProps<"/[lang]/vocab">) {
  const { lang } = await params;
  if (!isLang(lang)) notFound();
  const tr = t(lang);
  const words = await getVocab();
  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-bold">{tr("navVocab")}</h1>
        <p className="mt-1 text-sm text-muted">{tr("vocabNote")}</p>
      </div>
      <VocabList words={words} lang={lang} />
    </div>
  );
}
