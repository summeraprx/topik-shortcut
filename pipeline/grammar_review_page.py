"""Build a local page for the owner to review Claude's grammar labels.

Input:  data/processed/analysis/grammar_candidates.json  (auto-mined, from analyze.py)
        content/grammar/grammar_labels.json              (Claude's names / meanings / groups)
Output: data/review/grammar_review.html   (open in a browser; "Save" downloads grammar_review.json)
Run:    .venv/bin/python pipeline/grammar_review_page.py
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CANDIDATES = ROOT / "data" / "processed" / "analysis" / "grammar_candidates.json"
LABELS = ROOT / "content" / "grammar" / "grammar_labels.json"
DETAILS = sorted((ROOT / "content" / "grammar").glob("grammar_details_*.json"))
RULE_MARK = {"ok": "✓", "no": "✗", "note": "•"}
OUT = ROOT / "data" / "review" / "grammar_review.html"
GRAMMAR_QUESTIONS = re.compile(r"^\d+-reading-[1-4]$")   # Reading Q1–4 test grammar directly
SHOW_FIRST = 5   # examples visible before "Show all"


def build():
    cands = {c["pattern"]: c for c in json.loads(CANDIDATES.read_text())}
    labels = json.loads(LABELS.read_text())

    covered = [m for g in labels["groups"] for m in g["members"]] + list(labels["dropped"])
    missing = set(cands) - set(covered)
    if missing:
        raise SystemExit(f"Not labelled yet: {sorted(missing)}")

    details = {}
    for f in DETAILS:
        details.update(json.loads(f.read_text()))

    def text_blocks(d, lang):
        """Form / rules / similar as editable text, one item per line."""
        rules = "\n".join(f"{RULE_MARK[r['t']]} {r[lang]}" for r in d.get("rules", []))
        similar = "\n".join(f"≈ {s['g']}" for s in d.get("similar", []))     # names only (owner's style)
        return {f"form_{lang}": d.get("form", {}).get(lang, ""), f"rules_{lang}": rules, f"similar_{lang}": similar,
                f"note_{lang}": d.get("note", {}).get(lang, "")}

    groups = []
    for i, g in enumerate(labels["groups"]):
        d = details.get(g["name"], {})
        members = [cands[m] for m in g["members"]]
        examples, seen = [], set()
        for m in members:
            for e in m["examples"]:
                if e["sentence"] not in seen:
                    seen.add(e["sentence"])
                    examples.append(e)
        # newest round first, then question number
        examples.sort(key=lambda e: (-int(e["source"].split("-")[0]), int(e["source"].split("-")[-1])))
        tested = sorted({q for m in members for q in m["questions"] if GRAMMAR_QUESTIONS.match(q)})
        groups.append({
            "id": f"g{i}", "name": g["name"], "en": g["en"], "th": g["th"], "note": g.get("note", ""),
            "count": sum(m["count"] for m in members),
            "rounds": sorted({r for m in members for r in m["rounds"]}),
            "members": [{"pattern": m["pattern"], "count": m["count"]} for m in members],
            "tested": tested, "examples": examples,
            "exam_pair": any(s.get("exam") for s in d.get("similar", [])),
            **text_blocks(d, "en"), **text_blocks(d, "th"),
        })
    groups.sort(key=lambda g: (not g["tested"], -g["count"]))
    dropped = [{"pattern": p, "reason": r, "count": cands[p]["count"],
                "example": cands[p]["examples"][0]["sentence"]} for p, r in labels["dropped"].items()]

    html = TEMPLATE.replace("__GROUPS__", json.dumps(groups, ensure_ascii=False)) \
                   .replace("__DROPPED__", json.dumps(dropped, ensure_ascii=False)) \
                   .replace("__SHOW_FIRST__", str(SHOW_FIRST))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html, encoding="utf-8")
    n_tested = sum(bool(g["tested"]) for g in groups)
    print(f"{len(groups)} grammar points ({n_tested} appear in Q1–4), {len(dropped)} dropped -> {OUT}")


TEMPLATE = r"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Grammar Label Review</title>
<style>
:root {
  --bg: #f6f6f4; --card: #ffffff; --ink: #1d1d1b; --muted: #6b6b66; --line: #e2e1dc;
  --ok: #1f7a4d; --ok-bg: #e3f3ea; --bad: #b3261e; --bad-bg: #fbe7e5; --edit: #8a5a00; --edit-bg: #fff1d6;
  --accent: #2f5bd3; --tag-bg: #eef1fb;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg: #161615; --card: #222220; --ink: #ecebe6; --muted: #a3a29b; --line: #3a3936;
    --ok: #6fcf97; --ok-bg: #1d3328; --bad: #f2867d; --bad-bg: #3b2220; --edit: #f0c36a; --edit-bg: #3a3019;
    --accent: #8aa8ff; --tag-bg: #262b3a;
  }
}
:root[data-theme="dark"] {
  --bg: #161615; --card: #222220; --ink: #ecebe6; --muted: #a3a29b; --line: #3a3936;
  --ok: #6fcf97; --ok-bg: #1d3328; --bad: #f2867d; --bad-bg: #3b2220; --edit: #f0c36a; --edit-bg: #3a3019;
  --accent: #8aa8ff; --tag-bg: #262b3a;
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--ink);
  font: 15px/1.6 -apple-system, "Apple SD Gothic Neo", "Noto Sans KR", "Noto Sans Thai", system-ui, sans-serif; }
header { position: sticky; top: 0; z-index: 5; background: var(--card); border-bottom: 1px solid var(--line);
  padding: 12px 16px; display: flex; flex-wrap: wrap; gap: 10px; align-items: center; }
header h1 { font-size: 17px; margin: 0 12px 0 0; }
.progress { color: var(--muted); font-variant-numeric: tabular-nums; }
.bar { flex: 1 1 160px; height: 6px; background: var(--line); border-radius: 3px; overflow: hidden; }
.bar > div { height: 100%; background: var(--ok); width: 0; transition: width .2s; }
button { font: inherit; color: var(--ink); background: var(--card); border: 1px solid var(--line);
  border-radius: 8px; padding: 6px 12px; cursor: pointer; }
button.primary { background: var(--accent); color: #fff; border-color: var(--accent); }
main { max-width: 980px; margin: 0 auto; padding: 16px; }
h2.section { font-size: 18px; margin: 28px 0 4px; }
p.help, .sub { color: var(--muted); margin: 0 0 14px; }
.card { background: var(--card); border: 1px solid var(--line); border-left-width: 4px; border-radius: 12px;
  padding: 14px 16px; margin-bottom: 14px; }
.card.ok { border-left-color: var(--ok); } .card.edit { border-left-color: var(--edit); } .card.bad { border-left-color: var(--bad); }
.top { display: flex; flex-wrap: wrap; justify-content: space-between; gap: 8px; align-items: flex-start; }
.stats { color: var(--muted); font-size: 13px; }
.badge { display: inline-block; background: var(--tag-bg); color: var(--accent); border-radius: 6px; padding: 1px 8px;
  font-size: 12px; margin-right: 6px; }
.badge.test { background: var(--edit-bg); color: var(--edit); font-weight: 600; }
.state button { padding: 3px 10px; }
.state button.on.ok { background: var(--ok-bg); color: var(--ok); border-color: var(--ok); }
.state button.on.bad { background: var(--bad-bg); color: var(--bad); border-color: var(--bad); }
.edited { color: var(--edit); font-size: 13px; font-weight: 600; }
.grid { display: grid; grid-template-columns: 80px minmax(0, 1fr) minmax(0, 1fr); gap: 6px 10px; align-items: start; margin: 10px 0; }
.grid .head { color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: .04em; }
.grid .full { grid-column: 2 / 4; }
.grid label { color: var(--muted); font-size: 13px; }
input[type=text], textarea { width: 100%; font: inherit; color: var(--ink); background: var(--bg);
  border: 1px solid var(--line); border-radius: 6px; padding: 5px 8px; }
input.name { font-size: 17px; font-weight: 600; }
textarea { min-height: 38px; resize: vertical; }
.exhead { margin-top: 12px; font-weight: 600; font-size: 13px; color: var(--muted); }
button.more { margin-top: 6px; font-size: 13px; padding: 3px 10px; }
.examples { margin: 4px 0 0; padding: 0; list-style: none; }
.examples li { border-top: 1px dashed var(--line); padding: 6px 0; font-size: 14px; }
.examples .src { color: var(--muted); font-size: 12px; margin-left: 6px; white-space: nowrap; }
.pieces { font-family: ui-monospace, Menlo, monospace; font-size: 12px; color: var(--muted); }
.note { background: var(--edit-bg); border-radius: 6px; padding: 4px 8px; font-size: 13px; margin-top: 6px; }
.drop { display: grid; grid-template-columns: auto minmax(0, 1fr); gap: 4px 10px; align-items: start;
  background: var(--card); border: 1px solid var(--line); border-radius: 10px; padding: 10px 14px; margin-bottom: 8px; }
@media (max-width: 720px) { .grid { grid-template-columns: 1fr; } .grid .full { grid-column: auto; } .grid .head { display: none; } }
</style>
</head>
<body>
<header>
  <h1>Grammar label review</h1>
  <span class="progress" id="progress"></span>
  <div class="bar"><div id="barfill"></div></div>
  <button id="load">Load saved file</button>
  <button class="primary" id="save">Save review</button>
  <input type="file" id="file" accept=".json" hidden>
</header>
<main>
  <p class="help">For each grammar point: check the <b>grammar</b>, its <b>meaning</b>, <b>form</b> (how to attach -는/(으)ㄴ/(으)ㄹ), <b>rules</b> (✓ do · ✗ don't · • note) <b>similar</b> grammar and the <b>note</b> (how the similar grammar differs), in English and Thai, against the real examples. ⭐ = the exam itself paired them in Q3–4.
  ✅ = correct. Editing any box marks it ✏️ (your version is saved). ❌ = not useful for learners (drop it).
  The note box is optional (e.g. "merge with -는 바람에").</p>
  <div id="tested"></div>
  <div id="passages"></div>
  <h2 class="section">Dropped by Claude</h2>
  <p class="sub">Tick "restore" if any of these should be kept.</p>
  <div id="dropped"></div>
</main>
<script>
const GROUPS = __GROUPS__;
const DROPPED = __DROPPED__;
const KEY = "grammar-review-v1";
const SHOW_FIRST = __SHOW_FIRST__;
const EDITABLE = ["name", "en", "th", "form_en", "form_th", "rules_en", "rules_th", "similar_en", "similar_th", "note_en", "note_th"];
let state = {};
try { state = JSON.parse(localStorage.getItem(KEY) || "{}"); } catch (e) { state = {}; }
const rec = id => state[id] || (state[id] = { status: null, edits: {}, note: "", restore: false });

function persist() {
  try { localStorage.setItem(KEY, JSON.stringify(state)); } catch (e) {}
  const done = GROUPS.filter(g => state[g.id] && state[g.id].status).length;
  document.getElementById("progress").textContent = done + " / " + GROUPS.length + " reviewed";
  document.getElementById("barfill").style.width = (100 * done / GROUPS.length) + "%";
  for (const g of GROUPS) {
    const card = document.getElementById(g.id); if (!card) continue;
    const s = state[g.id] && state[g.id].status;
    card.className = "card" + (s ? " " + s : "");
  }
}

function field(g, key, cls, multi) {
  const r = rec(g.id);
  const el = document.createElement(key === "comment" || multi ? "textarea" : "input");
  if (el.tagName === "INPUT") el.type = "text";
  if (multi) el.rows = Math.max(1, (g[key] || "").split("\n").length);
  if (cls) el.className = cls;
  el.value = key === "comment" ? r.note : (key in r.edits ? r.edits[key] : g[key]);
  el.oninput = () => {
    if (key === "comment") { r.note = el.value; persist(); return; }
    if (el.value === g[key]) delete r.edits[key]; else r.edits[key] = el.value;
    r.status = Object.keys(r.edits).length ? "edit" : (r.status === "edit" ? null : r.status);
    persist(); renderState(g);
  };
  return el;
}

function renderState(g) {
  const r = rec(g.id), box = document.querySelector("#" + g.id + " .state");
  box.innerHTML = "";
  for (const [s, label, title] of [["ok", "✅", "Correct"], ["bad", "❌", "Not useful: drop"]]) {
    const b = document.createElement("button"); b.textContent = label; b.title = title; b.className = s;
    if (r.status === s) b.classList.add("on");
    b.onclick = () => { r.status = s; if (s === "ok") r.edits = {}; persist(); render(g); };
    box.appendChild(b);
  }
  if (r.status === "edit") { const e = document.createElement("span"); e.className = "edited"; e.textContent = " ✏️ edited"; box.appendChild(e); }
}

function render(g) {
  const card = document.getElementById(g.id);
  card.innerHTML = "";
  const top = document.createElement("div"); top.className = "top";
  const left = document.createElement("div");
  left.innerHTML = (g.tested.length ? `<span class="badge test">In Q1–4: ${g.tested.map(q => q.replace("-reading-", " Q")).join(", ")}</span>` : "")
    + (g.exam_pair ? `<span class="badge test">⭐ exam pair</span>` : "")
    + `<span class="badge">${g.count}× in ${g.rounds.length} round${g.rounds.length > 1 ? "s" : ""}</span>`;
  const st = document.createElement("div"); st.className = "state";
  top.append(left, st); card.appendChild(top);

  const grid = document.createElement("div"); grid.className = "grid";
  const add = (label, ...els) => { const l = document.createElement("label"); l.textContent = label; grid.append(l, ...els); };
  const name = field(g, "name", "name"); name.classList.add("full"); add("Grammar", name);
  const h0 = document.createElement("span"), h1 = document.createElement("span"), h2 = document.createElement("span");
  h1.className = h2.className = "head"; h1.textContent = "English"; h2.textContent = "ภาษาไทย"; grid.append(h0, h1, h2);
  add("Meaning", field(g, "en"), field(g, "th"));
  for (const [k, label] of [["form", "Form"], ["rules", "Rules"], ["similar", "Similar"], ["note", "Note"]])
    if (g[k + "_en"] || g[k + "_th"]) add(label, field(g, k + "_en", "", true), field(g, k + "_th", "", true));
  const note = field(g, "comment"); note.classList.add("full"); note.placeholder = "Optional: a question or instruction for Claude"; add("Comment", note);
  card.appendChild(grid);
  if (g.note) { const n = document.createElement("div"); n.className = "note"; n.textContent = "Claude: " + g.note; card.appendChild(n); }
  const pieces = document.createElement("div"); pieces.className = "pieces";
  pieces.textContent = "Kiwi pieces: " + g.members.map(m => `${m.pattern} (${m.count})`).join("  ·  ");
  card.appendChild(pieces);
  const h = document.createElement("div"); h.className = "exhead";
  h.textContent = `Same grammar in other exam questions (${g.examples.length})`;
  const ul = document.createElement("ul"); ul.className = "examples";
  g.examples.forEach((e, i) => {
    const li = document.createElement("li"); li.textContent = e.sentence;
    if (i >= SHOW_FIRST) li.hidden = true;
    const s = document.createElement("span"); s.className = "src"; s.textContent = e.source.replace("-reading-", " Q").replace("-writing-", " W");
    li.appendChild(s); ul.appendChild(li);
  });
  card.append(h, ul);
  if (g.examples.length > SHOW_FIRST) {
    const more = document.createElement("button"); more.className = "more";
    more.textContent = `Show all ${g.examples.length}`;
    more.onclick = () => { ul.querySelectorAll("li[hidden]").forEach(li => li.hidden = false); more.remove(); };
    card.appendChild(more);
  }
  renderState(g); persist();
}

function build() {
  const tested = document.getElementById("tested"), passages = document.getElementById("passages");
  const nT = GROUPS.filter(g => g.tested.length).length;
  tested.innerHTML = `<h2 class="section">① Appears in Reading Q1–4, the grammar questions (${nT})</h2><p class="sub">Found in the question sentence or the choices of Q1–4. Not every one is the tested answer: check the examples.</p>`;
  passages.innerHTML = `<h2 class="section">② Used in passages (${GROUPS.length - nT})</h2><p class="sub">Grammar that appears in reading passages and writing prompts.</p>`;
  for (const g of GROUPS) {
    const card = document.createElement("section"); card.className = "card"; card.id = g.id;
    (g.tested.length ? tested : passages).appendChild(card);
    render(g);
  }
  const dl = document.getElementById("dropped");
  for (const d of DROPPED) {
    const row = document.createElement("div"); row.className = "drop";
    const id = "drop:" + d.pattern;
    const cb = document.createElement("input"); cb.type = "checkbox"; cb.checked = rec(id).restore;
    cb.onchange = () => { rec(id).restore = cb.checked; persist(); };
    const lab = document.createElement("label"); lab.append(cb, " restore");
    const info = document.createElement("div");
    info.innerHTML = `<div class="pieces">${d.pattern} (${d.count}×)</div><div>${d.reason}</div><div class="sub" style="margin:0">e.g. ${d.example}</div>`;
    row.append(lab, info); dl.appendChild(row);
  }
  persist();
}

document.getElementById("save").onclick = () => {
  const out = { saved_at: new Date().toISOString(), groups: [], restored: [] };
  for (const g of GROUPS) {
    const r = state[g.id] || { status: null, edits: {}, note: "" };
    out.groups.push({ members: g.members.map(m => m.pattern), status: r.status || "unchecked",
      original: { name: g.name, en: g.en, th: g.th },
      final: Object.fromEntries(EDITABLE.map(k => [k, r.edits[k] ?? g[k]])),
      edited: Object.keys(r.edits), note: r.note || "" });
  }
  for (const d of DROPPED) if (state["drop:" + d.pattern] && state["drop:" + d.pattern].restore) out.restored.push(d.pattern);
  const blob = new Blob([JSON.stringify(out, null, 1)], { type: "application/json" });
  const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = "grammar_review.json"; a.click();
};
document.getElementById("load").onclick = () => document.getElementById("file").click();
document.getElementById("file").onchange = async (e) => {
  const f = e.target.files[0]; if (!f) return;
  const saved = JSON.parse(await f.text()); state = {};
  saved.groups.forEach(sg => {
    const g = GROUPS.find(x => x.members.map(m => m.pattern).join("|") === sg.members.join("|")); if (!g) return;
    const r = rec(g.id); r.status = sg.status === "unchecked" ? null : sg.status; r.note = sg.note || "";
    for (const k of EDITABLE) if (k in sg.final && sg.final[k] !== g[k]) r.edits[k] = sg.final[k];
  });
  (saved.restored || []).forEach(p => rec("drop:" + p).restore = true);
  document.getElementById("tested").innerHTML = ""; document.getElementById("passages").innerHTML = ""; document.getElementById("dropped").innerHTML = "";
  build();
};
build();
</script>
</body>
</html>
"""

if __name__ == "__main__":
    build()
