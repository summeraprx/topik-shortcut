"use client";

import { useMemo, useRef, useState } from "react";

// 원고지 answer box, like the TOPIK answer sheet: 25 cells per row, one character per cell,
// a space takes a cell. Writing starts in the first cell: the writer types the indent space
// at the start of each paragraph themselves (it counts as a character). A new paragraph (Enter)
// starts a new row; a space that only wraps onto the start of a row is not written.
// Arabic numerals go two per cell, paired from the left (2019 -> 20|19, 340 -> 34|0), as in
// rule 4 of the official guide. The counter still counts each digit (the official counts do).
// Typing goes into a transparent textarea laid over the grid (so Korean input works normally).
const COLS = 25;

type Cell = { ch: string; index: number | null }; // index = position in the text (null = empty cell)

function layout(text: string) {
  const cells: Cell[] = [];
  const cellOf: number[] = new Array(text.length + 1).fill(0);
  let paragraphStart = true;
  let digitCell: number | null = null; // cell holding a single digit that the next digit can join
  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    const digit = ch >= "0" && ch <= "9";
    if (digit && digitCell !== null) {
      cells[digitCell].ch += ch;
      cellOf[i] = digitCell;
      digitCell = null;
      continue;
    }
    if (ch === "\n") {
      cellOf[i] = cells.length;
      while (cells.length % COLS !== 0) cells.push({ ch: "", index: null });
      paragraphStart = true;
      digitCell = null;
      continue;
    }
    cellOf[i] = cells.length;
    // a space wrapping onto the start of a row is not written (but the typed indent is)
    if (ch === " " && cells.length % COLS === 0 && !paragraphStart) continue;
    cells.push({ ch, index: i });
    paragraphStart = false;
    digitCell = digit ? cells.length - 1 : null;
  }
  cellOf[text.length] = digitCell ?? cells.length;
  return { cells, cellOf };
}

export default function Wongoji({ value, onChange, minRows }: { value: string; onChange: (v: string) => void; minRows: number }) {
  const [caret, setCaret] = useState(0);
  const [focused, setFocused] = useState(false);
  const area = useRef<HTMLTextAreaElement>(null);
  const grid = useRef<HTMLDivElement>(null);
  const { cells, cellOf } = useMemo(() => layout(value), [value]);
  const rows = Math.max(minRows, Math.ceil((cells.length + 2) / COLS));
  const caretCell = cellOf[Math.min(caret, value.length)];

  function sync() {
    if (area.current) setCaret(area.current.selectionStart);
  }

  // Click on a cell -> put the caret at the character in (or after) that cell
  function placeCaret(e: React.MouseEvent<HTMLTextAreaElement>) {
    const box = grid.current?.getBoundingClientRect();
    if (!box || !area.current) return;
    const col = Math.min(COLS - 1, Math.max(0, Math.floor(((e.clientX - box.left) / box.width) * COLS)));
    const row = Math.max(0, Math.floor(((e.clientY - box.top) / box.height) * rows));
    const target = row * COLS + col;
    let pos = value.length;
    for (let i = 0; i <= value.length; i++) {
      if (cellOf[i] >= target) { pos = i; break; }
    }
    area.current.setSelectionRange(pos, pos);
    setCaret(pos);
  }

  return (
    <div className="flex gap-1">
      <div ref={grid} className={`relative flex-1 rounded-md border bg-card ${focused ? "border-accent" : "border-line"}`}>
        <div className="grid" style={{ gridTemplateColumns: `repeat(${COLS}, minmax(0, 1fr))` }} aria-hidden="true">
          {Array.from({ length: rows * COLS }, (_, i) => (
            <div
              key={i}
              className={`flex aspect-square items-center justify-center border-r border-b border-line text-[clamp(10px,2.6vw,18px)] leading-none tracking-tighter ${
                focused && i === caretCell ? "bg-accent-soft" : ""
              } ${i % COLS === COLS - 1 ? "border-r-0" : ""}`}
            >
              {cells[i]?.ch}
            </div>
          ))}
        </div>
        <textarea
          ref={area}
          value={value}
          onChange={(e) => { onChange(e.target.value); setCaret(e.target.selectionStart); }}
          onSelect={sync}
          onKeyUp={sync}
          onMouseUp={placeCaret}
          onFocus={() => { setFocused(true); sync(); }}
          onBlur={() => setFocused(false)}
          spellCheck={false}
          aria-label="원고지"
          className="absolute inset-0 h-full w-full cursor-text resize-none text-base opacity-0"
        />
      </div>
      <div className="flex w-7 flex-col text-[10px] text-muted" aria-hidden="true">
        {Array.from({ length: rows }, (_, r) => (
          <div key={r} className="flex flex-1 items-end">{(r + 1) % 2 === 0 ? (r + 1) * COLS : ""}</div>
        ))}
      </div>
    </div>
  );
}
