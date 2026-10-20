"use client";

import { useState } from "react";

// Buttons that open one section at a time. defaultOpen: index of the section shown on entry (or none).
export default function ToggleSections({ sections, defaultOpen = null }: { sections: { label: string; content: React.ReactNode }[]; defaultOpen?: number | null }) {
  const [open, setOpen] = useState<number | null>(defaultOpen);
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2">
        {sections.map((s, i) => (
          <button
            key={s.label}
            onClick={() => setOpen(open === i ? null : i)}
            aria-expanded={open === i}
            className={`rounded-lg px-4 py-2 font-medium ${open === i ? "bg-accent text-white" : "border border-line bg-card hover:border-accent"}`}
          >
            {s.label}
          </button>
        ))}
      </div>
      {open !== null && <div>{sections[open].content}</div>}
    </div>
  );
}
