"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { LANGS, LANG_NAME, type Lang } from "@/lib/i18n";

// Same page in another language: /ko/grammar/3 -> /th/grammar/3
export default function LangSwitch({ current }: { current: Lang }) {
  const path = usePathname();
  const rest = path.split("/").slice(2).join("/");
  return (
    <div className="flex gap-1 text-sm">
      {LANGS.map((l) => (
        <Link
          key={l}
          href={`/${l}/${rest}`}
          className={`rounded-md px-2 py-1 ${l === current ? "bg-accent text-white" : "text-muted hover:bg-accent-soft"}`}
        >
          {LANG_NAME[l]}
        </Link>
      ))}
    </div>
  );
}
