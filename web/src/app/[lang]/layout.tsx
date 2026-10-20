import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import "../globals.css";
import LangSwitch from "@/components/LangSwitch";
import { LANGS, isLang, t, type Key } from "@/lib/i18n";

export const metadata: Metadata = {
  title: "TOPIK Shortcut",
  description: "TOPIK II past-exam analysis, grammar, Ask TOPIK and a writing checker",
};

export function generateStaticParams() {
  return LANGS.map((lang) => ({ lang }));
}

const NAV: [string, Key][] = [
  ["", "navHome"],
  ["types", "navTypes"],
  ["grammar", "navGrammar"],
  ["vocab", "navVocab"],
  ["ask", "navAsk"],
  ["writing", "navWriting"],
];

export default async function LangLayout({ children, params }: LayoutProps<"/[lang]">) {
  const { lang } = await params;
  if (!isLang(lang)) notFound();
  const tr = t(lang);
  return (
    <html lang={lang}>
      <body className="min-h-screen font-sans antialiased">
        <header className="sticky top-0 z-10 border-b border-line bg-card/95 backdrop-blur">
          <div className="mx-auto flex max-w-5xl flex-wrap items-center gap-x-4 gap-y-2 px-4 py-3">
            <Link href={`/${lang}`} className="text-lg font-bold text-accent">
              {tr("appName")}
            </Link>
            <nav className="order-3 flex w-full gap-1 overflow-x-auto text-sm sm:order-2 sm:w-auto">
              {NAV.slice(1).map(([href, key]) => (
                <Link key={href} href={`/${lang}/${href}`} className="whitespace-nowrap rounded-md px-2 py-1 hover:bg-accent-soft">
                  {tr(key)}
                </Link>
              ))}
            </nav>
            <div className="order-2 ml-auto sm:order-3">
              <LangSwitch current={lang} />
            </div>
          </div>
        </header>
        <main className="mx-auto max-w-5xl px-4 py-6">{children}</main>
        <footer className="mx-auto max-w-5xl px-4 pb-8 text-xs text-muted">
          {tr("notReviewed")} · TOPIK II 102 · 96 · 91 · © 국립국제교육원 (NIIED)
        </footer>
      </body>
    </html>
  );
}
