import { notFound } from "next/navigation";
import WritingChecker from "@/components/WritingChecker";
import { isLang, t } from "@/lib/i18n";

export default async function WritingPage({ params }: PageProps<"/[lang]/writing">) {
  const { lang } = await params;
  if (!isLang(lang)) notFound();
  const tr = t(lang);
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">{tr("navWriting")}</h1>
      <WritingChecker lang={lang} />
    </div>
  );
}
