"""Build a local review page to check one round by hand (the "gold set").

For every question: the page image crop on the left, the extracted data on the right.
The reviewer marks each field correct / wrong, fixes wrong values, then saves a JSON file.
That file (data/gold/<round>.json) is the ground truth used by eval/eval_extraction.py.

Output: data/review/review_<round>.html  (local file, open in a browser, works offline)
Run:    .venv/bin/python pipeline/review_page.py 102
"""
import base64
import io
import json
import sys
from pathlib import Path

import pymupdf
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
OUT = ROOT / "data" / "review"
DPI = 110


def booklet_pdf(rnd, section):
    pattern = {"reading": f"*{rnd}회*읽기*.pdf", "writing": f"*{rnd}회*듣기,쓰기*.pdf"}[section]
    return pymupdf.open(sorted(RAW.glob(pattern))[0])


def crop(doc, page, top, bottom):
    pg = doc[page - 1]
    W, H = pg.rect.width, pg.rect.height
    clip = pymupdf.Rect(0.08 * W, max(0, top - 0.012) * H, 0.92 * W, min(1, bottom + 0.012) * H)
    img = Image.open(io.BytesIO(pg.get_pixmap(dpi=DPI, clip=clip).tobytes("png"))).convert("RGB")
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=72)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def build(rnd):
    questions = json.loads((PROCESSED / f"questions_{rnd}.json").read_text())
    docs = {s: booklet_pdf(rnd, s) for s in ("reading", "writing")}
    items, seen_groups = [], set()
    for q in questions:
        group = (q["section"], q["instruction"], q["shared_passage"])
        first_of_group = group not in seen_groups
        seen_groups.add(group)
        items.append({
            "id": f"{q['section']}-{q['number']}",
            "section": q["section"], "number": q["number"],
            "instruction": q["instruction"], "shared_passage": q["shared_passage"],
            "text": q["text"], "choices": q["choices"], "answer": q["answer"],
            "review_group": first_of_group,
            "warnings": q["warnings"] + [f"corrected by hand: {', '.join(q['corrected'])}"] * bool(q["corrected"]),
            "instruction_image": (crop(docs[q["section"]], *q["instruction_region"])
                                  if first_of_group and q["instruction_region"] else None),
            "images": [crop(docs[q["section"]], p, t, b) for p, t, b in q["regions"]],
        })
    html = TEMPLATE.replace("__ROUND__", str(rnd)).replace("__DATA__", json.dumps(items, ensure_ascii=False))
    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / f"review_{rnd}.html"
    out.write_text(html, encoding="utf-8")
    print(f"{len(items)} questions -> {out}  ({out.stat().st_size / 1e6:.1f} MB)")


TEMPLATE = r"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Gold Set Review</title>
<style>
:root {
  --bg: #f6f6f4; --card: #ffffff; --ink: #1d1d1b; --muted: #6b6b66; --line: #e2e1dc;
  --ok: #1f7a4d; --ok-bg: #e3f3ea; --bad: #b3261e; --bad-bg: #fbe7e5; --warn-bg: #fff4d6; --accent: #2f5bd3;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg: #161615; --card: #222220; --ink: #ecebe6; --muted: #a3a29b; --line: #3a3936;
    --ok: #6fcf97; --ok-bg: #1d3328; --bad: #f2867d; --bad-bg: #3b2220; --warn-bg: #3a321b; --accent: #8aa8ff;
  }
}
:root[data-theme="dark"] {
  --bg: #161615; --card: #222220; --ink: #ecebe6; --muted: #a3a29b; --line: #3a3936;
  --ok: #6fcf97; --ok-bg: #1d3328; --bad: #f2867d; --bad-bg: #3b2220; --warn-bg: #3a321b; --accent: #8aa8ff;
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--ink);
  font: 15px/1.6 -apple-system, "Apple SD Gothic Neo", "Noto Sans KR", system-ui, sans-serif; }
header { position: sticky; top: 0; z-index: 5; background: var(--card); border-bottom: 1px solid var(--line);
  padding: 12px 16px; display: flex; flex-wrap: wrap; gap: 10px; align-items: center; }
header h1 { font-size: 17px; margin: 0 12px 0 0; }
.progress { color: var(--muted); font-variant-numeric: tabular-nums; }
.bar { flex: 1 1 160px; height: 6px; background: var(--line); border-radius: 3px; overflow: hidden; }
.bar > div { height: 100%; background: var(--ok); width: 0; transition: width .2s; }
button, select { font: inherit; color: var(--ink); background: var(--card); border: 1px solid var(--line);
  border-radius: 8px; padding: 6px 12px; cursor: pointer; }
button.primary { background: var(--accent); color: #fff; border-color: var(--accent); }
main { max-width: 1280px; margin: 0 auto; padding: 16px; }
.help { color: var(--muted); margin: 0 0 16px; }
.card { background: var(--card); border: 1px solid var(--line); border-radius: 12px; margin-bottom: 18px;
  display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); }
.card.done { border-color: var(--ok); }
.imgs { padding: 12px; border-right: 1px solid var(--line); }
.imgs img.instr { border: 2px solid var(--accent); }
.imgs img { width: 100%; display: block; border-radius: 6px; margin-bottom: 8px; background: #fff; }
.fields { padding: 12px 16px; }
.qhead { display: flex; justify-content: space-between; align-items: center; gap: 8px; margin-bottom: 8px; }
.qhead h2 { font-size: 16px; margin: 0; }
.warn { background: var(--warn-bg); border-radius: 6px; padding: 4px 8px; font-size: 13px; margin-bottom: 8px; }
.field { border-top: 1px solid var(--line); padding: 10px 0; }
.field .label { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
.field .name { font-weight: 600; font-size: 13px; color: var(--muted); text-transform: uppercase; letter-spacing: .03em; }
.state button { padding: 2px 10px; }
.state button.on.ok { background: var(--ok-bg); color: var(--ok); border-color: var(--ok); }
.state button.on.bad { background: var(--bad-bg); color: var(--bad); border-color: var(--bad); }
textarea, input[type=text] { width: 100%; font: inherit; color: var(--ink); background: var(--bg);
  border: 1px solid var(--line); border-radius: 6px; padding: 6px 8px; }
textarea { min-height: 70px; resize: vertical; }
.choices input { margin-bottom: 4px; }
.same { color: var(--muted); font-size: 13px; }
@media (max-width: 760px) {
  .card { grid-template-columns: 1fr; }
  .imgs { border-right: 0; border-bottom: 1px solid var(--line); }
}
</style>
</head>
<body>
<header>
  <h1>Gold set review: round __ROUND__</h1>
  <span class="progress" id="progress"></span>
  <div class="bar"><div id="barfill"></div></div>
  <button id="load">Load saved file</button>
  <button class="primary" id="save">Save gold file</button>
  <input type="file" id="file" accept=".json" hidden>
</header>
<main>
  <p class="help">Compare the image with the extracted fields. Click ✅ if a field is correct, ❌ if wrong.
  Editing a field marks it ❌ and keeps your corrected value. "All correct" marks every field of a question ✅.
  Small OCR typos count as wrong — fix them in the box. Answers are not reviewed here (you already checked the answer key).</p>
  <div id="list"></div>
</main>
<script>
const ROUND = __ROUND__;
const DATA = __DATA__;
const KEY = "gold-review-" + ROUND;
let state = {};
try { state = JSON.parse(localStorage.getItem(KEY) || "{}"); } catch (e) { state = {}; }

function fieldsOf(q) {
  const f = [];
  if (q.review_group && q.instruction) f.push("instruction");
  if (q.review_group && q.shared_passage) f.push("shared_passage");
  f.push("text");
  if (q.section === "reading") f.push("choices");
  return f;
}
const LABEL = { instruction: "Instruction", shared_passage: "Shared passage", text: "Question text",
                choices: "Choices ① ② ③ ④", answer: "Answer" };

function persist() {
  try { localStorage.setItem(KEY, JSON.stringify(state)); } catch (e) {}
  updateProgress();
}
function rec(id) { return state[id] || (state[id] = { status: {}, value: {} }); }

function updateProgress() {
  let done = 0;
  for (const q of DATA) {
    const r = state[q.id];
    const complete = r && fieldsOf(q).every(f => r.status[f]);
    if (complete) done++;
    const card = document.getElementById("card-" + q.id);
    if (card) card.classList.toggle("done", !!complete);
  }
  document.getElementById("progress").textContent = done + " / " + DATA.length + " reviewed";
  document.getElementById("barfill").style.width = (100 * done / DATA.length) + "%";
}

function stateButtons(q, f) {
  const wrap = document.createElement("span");
  wrap.className = "state";
  for (const [s, label] of [["ok", "✅"], ["bad", "❌"]]) {
    const b = document.createElement("button");
    b.textContent = label; b.className = s;
    b.onclick = () => { rec(q.id).status[f] = s; persist(); render(q); };
    if (rec(q.id).status[f] === s) b.classList.add("on");
    wrap.appendChild(b);
  }
  return wrap;
}

function markEdited(q, f, value) {
  const r = rec(q.id);
  r.value[f] = value; r.status[f] = "bad"; persist();
  const btns = document.querySelectorAll(`#card-${CSS.escape(q.id)} [data-field="${f}"] .state button`);
  btns.forEach(b => b.classList.toggle("on", b.classList.contains("bad")));
}

function editor(q, f) {
  const r = rec(q.id);
  const current = f in r.value ? r.value[f] : q[f];
  if (f === "choices") {
    const box = document.createElement("div"); box.className = "choices";
    const vals = [...(current || [])]; while (vals.length < 4) vals.push("");
    vals.slice(0, 4).forEach((v, i) => {
      const inp = document.createElement("input"); inp.type = "text"; inp.value = v;
      inp.oninput = () => { vals[i] = inp.value; markEdited(q, f, vals.slice(0, 4)); };
      box.appendChild(inp);
    });
    return box;
  }
  if (f === "answer") {
    const sel = document.createElement("select");
    for (const n of [1, 2, 3, 4]) {
      const o = document.createElement("option"); o.value = n; o.textContent = "①②③④"[n - 1];
      if (n === current) o.selected = true; sel.appendChild(o);
    }
    sel.onchange = () => markEdited(q, f, Number(sel.value));
    return sel;
  }
  const ta = document.createElement("textarea"); ta.value = current || "";
  ta.rows = Math.min(12, Math.max(2, Math.ceil((current || "").length / 45)));
  ta.oninput = () => markEdited(q, f, ta.value);
  return ta;
}

function render(q) {
  const card = document.getElementById("card-" + q.id);
  const fields = card.querySelector(".fields");
  fields.innerHTML = "";
  const head = document.createElement("div"); head.className = "qhead";
  head.innerHTML = `<h2>${q.section === "reading" ? "Reading" : "Writing"} Q${q.number}</h2>`;
  const all = document.createElement("button"); all.textContent = "All correct";
  all.onclick = () => { const r = rec(q.id); fieldsOf(q).forEach(f => { r.status[f] = "ok"; delete r.value[f]; }); persist(); render(q); };
  head.appendChild(all); fields.appendChild(head);
  for (const w of q.warnings) {
    const d = document.createElement("div"); d.className = "warn"; d.textContent = "⚠ " + w; fields.appendChild(d);
  }
  if (!q.review_group && (q.instruction || q.shared_passage)) {
    const s = document.createElement("div"); s.className = "same";
    s.textContent = "Instruction and shared passage: same as the previous question in this group (review there).";
    fields.appendChild(s);
  }
  if (q.section === "reading" && q.answer) {
    const a = document.createElement("div"); a.className = "same";
    a.textContent = "Answer: " + "①②③④"[q.answer - 1] + " (from the answer key, already checked on the audit sheet: not reviewed here)";
    fields.appendChild(a);
  }
  for (const f of fieldsOf(q)) {
    const box = document.createElement("div"); box.className = "field"; box.dataset.field = f;
    const label = document.createElement("div"); label.className = "label";
    const name = document.createElement("span"); name.className = "name"; name.textContent = LABEL[f];
    label.append(name, stateButtons(q, f));
    box.append(label, editor(q, f));
    fields.appendChild(box);
  }
  updateProgress();
}

function build() {
  const list = document.getElementById("list");
  for (const q of DATA) {
    const card = document.createElement("section"); card.className = "card"; card.id = "card-" + q.id;
    const imgs = document.createElement("div"); imgs.className = "imgs";
    if (q.instruction_image) {
      const cap = document.createElement("div"); cap.className = "same"; cap.textContent = "Instruction line:";
      const im = new Image(); im.src = q.instruction_image; im.alt = "instruction"; im.className = "instr";
      imgs.append(cap, im);
      const cap2 = document.createElement("div"); cap2.className = "same"; cap2.textContent = "Question:"; imgs.appendChild(cap2);
    }
    for (const src of q.images) { const im = new Image(); im.src = src; im.alt = "Q" + q.number + " page crop"; im.loading = "lazy"; imgs.appendChild(im); }
    const fields = document.createElement("div"); fields.className = "fields";
    card.append(imgs, fields); list.appendChild(card);
    render(q);
  }
}

document.getElementById("save").onclick = () => {
  const out = { round: ROUND, saved_at: new Date().toISOString(), questions: {} };
  for (const q of DATA) {
    const r = state[q.id] || { status: {}, value: {} };
    const entry = {};
    for (const f of fieldsOf(q)) {
      entry[f] = { status: r.status[f] || "unchecked", extracted: q[f],
                   gold: f in r.value ? r.value[f] : (r.status[f] === "ok" ? q[f] : null) };
    }
    out.questions[q.id] = entry;
  }
  const blob = new Blob([JSON.stringify(out, null, 1)], { type: "application/json" });
  const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = ROUND + ".json"; a.click();
};
document.getElementById("load").onclick = () => document.getElementById("file").click();
document.getElementById("file").onchange = async (e) => {
  const file = e.target.files[0]; if (!file) return;
  const saved = JSON.parse(await file.text());
  state = {};
  for (const [id, entry] of Object.entries(saved.questions || {})) {
    const r = rec(id);
    for (const [f, v] of Object.entries(entry)) {
      if (v.status !== "unchecked") r.status[f] = v.status;
      if (v.status === "bad" && v.gold !== null) r.value[f] = v.gold;
    }
  }
  persist(); DATA.forEach(render);
};
build();
</script>
</body>
</html>
"""

if __name__ == "__main__":
    build(int(sys.argv[1]) if len(sys.argv) > 1 else 102)
