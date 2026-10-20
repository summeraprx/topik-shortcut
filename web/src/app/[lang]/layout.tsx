import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import "../globals.css";
import LangPopup from "@/components/LangPopup";
import { LANGS, isLang, t, type Key } from "@/lib/i18n";

export const metadata: Metadata = {
  title: "TOPIK Shortcut",
  description: "TOPIK II past-exam analysis, grammar, Ask TOPIK and a writing checker",
};

export function generateStaticParams() {
  return LANGS.map((lang) => ({ lang }));
}

const NAV: [string, Key][] = [
  ["types", "navGeneral"],
  ["grammar", "navGrammar"],
  ["vocab", "navVocab"],
  ["writing", "navWriting"],
];

export default async function LangLayout({ children, params }: LayoutProps<"/[lang]">) {
  const { lang } = await params;
  if (!isLang(lang)) notFound();
  const tr = t(lang);
  return (
    <html lang={lang}>
      <body className="flex min-h-screen flex-col font-sans antialiased">
        <header className="sticky top-0 z-10 border-b border-line bg-card/95 backdrop-blur">
          <div className="mx-auto flex max-w-5xl flex-wrap items-center gap-x-4 gap-y-2 px-4 py-3">
            <Link href={`/${lang}`} className="text-lg font-bold text-accent">
              {tr("appName")}
            </Link>
            <nav className="flex w-full items-center gap-1 overflow-x-auto text-sm sm:w-auto">
              {NAV.map(([href, key]) => (
                <Link key={href} href={`/${lang}/${href}`} className="whitespace-nowrap rounded-md px-2 py-1 hover:bg-accent-soft">
                  {tr(key)}
                </Link>
              ))}
              {/* Ask TOPIK (RAG) stands out as a button */}
              <Link href={`/${lang}/ask`} className="ml-1 whitespace-nowrap rounded-lg bg-accent px-3 py-1.5 font-semibold text-white shadow-sm hover:opacity-90">
                {tr("navAsk")}
              </Link>
            </nav>
          </div>
        </header>
        <LangPopup current={lang} />
        <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-6">{children}</main>
        <footer className="mx-auto w-full max-w-5xl px-4 pb-8 text-xs text-muted">
          {tr("notReviewed")} · TOPIK II 102 · 96 · 91 · © 국립국제교육원 (NIIED)
        </footer>
      </body>
    </html>
  );
}
