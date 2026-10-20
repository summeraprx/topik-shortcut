"use client";

import { useState } from "react";

export type ExampleItem = { sentence: string; source: string };

// Real exam sentences, newest round first; the first few visible, the rest behind "Show all".
export default function Examples({ items, showAllLabel, first = 5 }: { items: ExampleItem[]; showAllLabel: string; first?: number }) {
  const [all, setAll] = useState(false);
  const shown = all ? items : items.slice(0, first);
  return (
    <div>
      <ul className="divide-y divide-dashed divide-line">
        {shown.map((e) => (
          <li key={e.source + e.sentence} className="py-2 text-sm">
            {e.sentence}
            <span className="ml-2 whitespace-nowrap text-xs text-muted">{e.source}</span>
          </li>
        ))}
      </ul>
      {!all && items.length > first && (
        <button onClick={() => setAll(true)} className="mt-2 rounded-md border border-line px-3 py-1 text-sm hover:border-accent">
          {showAllLabel} {items.length}
        </button>
      )}
    </div>
  );
}
