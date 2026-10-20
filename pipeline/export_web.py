"""Export what the website needs into data/web/ (NOT in git: it contains exam text).

  overview.json   rounds, counts, question-type map, answer distribution
  grammar.json    98 grammar points: labels + details + where they appear + exam sentences
  vocab.json      most frequent words with counts, rounds, where, examples
  questions.json  every structured question (for links and the writing page)

Run: .venv/bin/python -m pipeline.export_web
"""
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "data" / "processed"
ANALYSIS = PROCESSED / "analysis"
CONTENT = ROOT / "content" / "grammar"
OUT = ROOT / "data" / "web"
ROUNDS = [102, 96, 91]


def load(path):
    return json.loads(Path(path).read_text())


def overview(questions):
    types = load(ANALYSIS / "question_types.json")
    rows = []
    for name, by_round in types.items():
        section, instruction = name.split(": ", 1)
        numbers = sorted({n for nums in by_round.values() for n in nums})
        rows.append({"section": section, "instruction": instruction, "numbers": numbers,
                     "same_in_all_rounds": len({tuple(v) for v in by_round.values()}) == 1 and len(by_round) == len(ROUNDS)})
    rows += [{"section": "writing", "instruction": str(n), "numbers": [n], "same_in_all_rounds": True} for n in (53, 54)]
    rows.sort(key=lambda r: (r["section"] != "reading", r["numbers"][0]))
    labels = {t["match"]: t for t in load(ROOT / "content" / "question_types.json")["types"]}
    for r in rows:
        t = labels.get(r["instruction"], {})
        r["task"], r["words"] = t.get("task", {}), t.get("words", [])
    # instruction groups as printed in the exam ([1~2], [3~4] …), identical in all analysed rounds
    by_instruction = {r["instruction"]: r for r in rows}
    groups = []
    for q in questions:
        if q["round"] != ROUNDS[0]:
            continue
        m = re.match(r"※ \[(\d+)~(\d+)\]", q["instruction"] or "")
        lo, hi = (int(m.group(1)), int(m.group(2))) if m else (q["number"], q["number"])
        name = re.sub(r"^※\s*\[[^\]]*\]\s*|\(각\s*\d+\s*점\)\s*$", "", q["instruction"]).strip() if m else str(q["number"])
        if not any(g["lo"] == lo and g["section"] == q["section"] for g in groups):
            t = by_instruction.get(name, {})
            groups.append({"section": q["section"], "lo": lo, "hi": hi, "instruction": t.get("instruction", name),
                           "task": t.get("task", {}), "words": t.get("words", [])})
    keys = load(PROCESSED / "answer_keys.json")[str(ROUNDS[0])]
    parts = {"listening": len(keys["listening"]), "reading": len(keys["reading"]),
             "writing": sum(q["section"] == "writing" for q in questions if q["round"] == ROUNDS[0])}
    return {
        "rounds": ROUNDS,
        "parts": parts,
        "groups": groups,
        "counts": {"questions": len(questions),
                   "reading": sum(q["section"] == "reading" for q in questions),
                   "writing": sum(q["section"] == "writing" for q in questions),
                   "words": len(load(ANALYSIS / "vocab.json")),
                   "grammar": len(load(CONTENT / "grammar_labels.json")["groups"])},
        "question_types": rows,
        "answer_distribution": load(ANALYSIS / "answer_distribution.json"),
        "withheld": [f"{q['round']}-{q['section']}-{q['number']}" for q in questions if q["passage_withheld"]],
    }


def grammar():
    labels = load(CONTENT / "grammar_labels.json")
    details = {}
    for f in sorted(CONTENT.glob("grammar_details_*.json")):
        details.update(load(f))
    cands = {c["pattern"]: c for c in load(ANALYSIS / "grammar_candidates.json")}
    out = []
    for i, g in enumerate(labels["groups"]):
        members = [cands[m] for m in g["members"] if m in cands]
        examples, seen = [], set()
        for m in members:
            for e in m["examples"]:
                if e["sentence"] not in seen:
                    seen.add(e["sentence"])
                    examples.append(e)
        examples.sort(key=lambda e: (-int(e["source"].split("-")[0]), int(e["source"].split("-")[-1])))
        questions = sorted({q for m in members for q in m["questions"]})
        d = details.get(g["name"], {})
        out.append({
            "id": i, "name": g["name"], "meaning": {"en": g["en"], "th": g["th"]},
            "form": d.get("form", {}), "rules": d.get("rules", []), "similar": d.get("similar", []),
            "note": d.get("note", {}), "count": sum(m["count"] for m in members),
            "rounds": sorted({r for m in members for r in m["rounds"]}),
            "in_q1_4": [q for q in questions if re.match(r"^\d+-reading-[1-4]$", q)],
            "questions": questions, "examples": examples, "reviewed": bool(g.get("reviewed")),
        })
    return out


def vocab():
    """All words, most frequent first, with their meaning (content/vocab, EN/TH)."""
    meanings = {}
    for f in sorted((ROOT / "content" / "vocab").glob("meanings_*.json")):
        meanings.update(load(f))
    return [{"lemma": r["lemma"], "pos": r["pos"], "count": r["count"],
             "meaning": dict(zip(("en", "th"), meanings.get(r["lemma"], ["", ""])))}
            for r in load(ANALYSIS / "vocab.json")]


def writing_images(questions):
    """Crop each Writing question (with its graph / picture) from the exam PDF -> data/web/writing/<round>-<n>.png
    Q53/54: the website shows the command as text, so the crop starts below the line ending in "(30점)"/"(50점)"."""
    import io
    import pymupdf
    from PIL import Image
    out_dir = OUT / "writing"
    out_dir.mkdir(parents=True, exist_ok=True)
    for q in questions:
        if q["section"] != "writing":
            continue
        pdf_path = sorted((ROOT / "data" / "raw").glob(f"*{q['round']}회*듣기,쓰기*.pdf"))[0]
        pdf = pymupdf.open(pdf_path)
        parts = []
        for k, (page, top, bottom) in enumerate(q["regions"]):
            if k == 0 and q["number"] in (53, 54):
                lines = load(ROOT / "data" / "ocr" / pdf_path.stem / f"page_{page:03d}.json")
                ends = [l["y"] + l["h"] for l in lines
                        if top - 0.01 <= l["y"] < bottom and re.search(r"\(\d+점\)", l["text"])]
                if ends:
                    top = min(ends) + 0.005
            pg = pdf[page - 1]
            W, H = pg.rect.width, pg.rect.height
            pad = 0 if (k == 0 and q["number"] in (53, 54)) else 0.015
            clip = pymupdf.Rect(0.08 * W, max(0, top - pad) * H, 0.92 * W, min(1, bottom + 0.015) * H)
            parts.append(Image.open(io.BytesIO(pg.get_pixmap(dpi=150, clip=clip).tobytes("png"))).convert("RGB"))
        img = Image.new("RGB", (max(p.width for p in parts), sum(p.height for p in parts)), "white")
        y = 0
        for part in parts:
            img.paste(part, (0, y))
            y += part.height
        img.save(out_dir / f"{q['round']}-{q['number']}.png", optimize=True)


def main():
    questions = [q for r in ROUNDS for q in load(PROCESSED / f"questions_{r}.json")]
    OUT.mkdir(parents=True, exist_ok=True)
    files = {"overview.json": overview(questions), "grammar.json": grammar(), "vocab.json": vocab(),
             "questions.json": [{k: q[k] for k in ("round", "section", "number", "instruction", "shared_passage",
                                                   "text", "choices", "answer", "points", "passage_withheld")}
                                for q in questions]}
    writing_images(questions)
    for name, data in files.items():
        (OUT / name).write_text(json.dumps(data, ensure_ascii=False))
        print(f"{name:16} {len(data) if isinstance(data, list) else 'object'}")


if __name__ == "__main__":
    main()
