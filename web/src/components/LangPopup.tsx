"use client";

import { useRouter, usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { LANGS, LANG_NAME, type Lang } from "@/lib/i18n";

// Shown on every open or reload of the site, not while moving between pages.
// After a choice we navigate to the same page in that language; a one-time flag stops the
// pop-up from showing again for that navigation.
const SKIP = "lang-popup-skip-once";

export default function LangPopup({ current }: { current: Lang }) {
  const [open, setOpen] = useState(false);
  const router = useRouter();
  const path = usePathname();

  useEffect(() => {
    let skip = false;
    try {
      skip = sessionStorage.getItem(SKIP) === "1";
      sessionStorage.removeItem(SKIP);
    } catch {}
    // eslint-disable-next-line react-hooks/set-state-in-effect -- open once after a full page load
    if (!skip) setOpen(true);
  }, []);

  if (!open) return null;

  function choose(lang: Lang) {
    setOpen(false);
    if (lang === current) return;
    try {
      sessionStorage.setItem(SKIP, "1");
    } catch {}
    router.push(`/${lang}/${path.split("/").slice(2).join("/")}`);
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4" role="dialog" aria-modal="true" aria-labelledby="lang-title">
      <div className="w-full max-w-xs rounded-2xl border border-line bg-card p-5 shadow-xl">
        <h2 id="lang-title" className="mb-4 text-center text-sm text-muted">
          Choose your language
        </h2>
        <div className="flex flex-col gap-2">
          {LANGS.map((l) => (
            <button
              key={l}
              onClick={() => choose(l)}
              className="rounded-lg border border-line px-4 py-3 text-lg font-medium hover:border-accent hover:bg-accent-soft"
            >
              {LANG_NAME[l]}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
