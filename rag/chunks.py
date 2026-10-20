"""Turn our data into "chunks": the pieces the search engine can find and the model can cite.

Two kinds of chunks:
  - exam question:  "102-reading-23"   instruction + passage + question + choices + answer
  - grammar card:   "grammar:-는 바람에"  meaning, form, rules, similar grammar, where it appears

Every chunk keeps its id, so an answer can cite it: [96-reading-3] or [grammar:-는 바람에].
"""
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "data" / "processed"
CONTENT = ROOT / "content" / "grammar"
CIRCLED = "①②③④"


def grammar_by_question():
    """question id -> names of grammar points used in it (from the Kiwi analysis + labels)."""
    labels = json.loads((CONTENT / "grammar_labels.json").read_text())
    group_of = {m: g["name"] for g in labels["groups"] for m in g["members"]}
    out = defaultdict(set)
    for c in json.loads((PROCESSED / "analysis" / "grammar_candidates.json").read_text()):
        if c["pattern"] in group_of:
            for q in c["questions"]:
                out[q].add(group_of[c["pattern"]])
    return out


def question_chunks(rounds):
    used = grammar_by_question()
    chunks = []
    for rnd in rounds:
        for q in json.loads((PROCESSED / f"questions_{rnd}.json").read_text()):
            qid = f"{q['round']}-{q['section']}-{q['number']}"
            parts = [f"TOPIK II 제{q['round']}회 {'읽기' if q['section'] == 'reading' else '쓰기'} {q['number']}번"]
            if q["instruction"]:
                parts.append(q["instruction"])
            if q["shared_passage"] and not q["passage_withheld"]:
                parts.append(q["shared_passage"])
            if q["text"]:
                parts.append(q["text"])
            if q["choices"]:
                parts.append("\n".join(f"{CIRCLED[i]} {c}" for i, c in enumerate(q["choices"])))
            if q["answer"]:
                parts.append(f"정답: {CIRCLED[q['answer'] - 1]} {q['choices'][q['answer'] - 1]}")
            chunks.append({
                "id": qid, "kind": "question", "text": "\n".join(parts),
                "meta": {"round": q["round"], "section": q["section"], "number": q["number"],
                         "grammar": sorted(used.get(qid, [])), "passage_withheld": q["passage_withheld"]},
            })
    return chunks


def grammar_chunks():
    labels = json.loads((CONTENT / "grammar_labels.json").read_text())
    details = {}
    for f in sorted(CONTENT.glob("grammar_details_*.json")):
        details.update(json.loads(f.read_text()))
    where = defaultdict(set)
    for qid, names in grammar_by_question().items():
        for n in names:
            where[n].add(qid)

    chunks = []
    for g in labels["groups"]:
        d = details.get(g["name"], {})
        lines = [f"문법: {g['name']}", f"Meaning: {g['en']}", f"ความหมาย: {g['th']}"]
        if d.get("form"):
            lines.append(f"Form: {d['form']['en']}")
        for r in d.get("rules", []):
            lines.append(f"Rule: {r['en']} / {r['th']}")
        if d.get("similar"):
            lines.append("Similar: " + ", ".join(s["g"] for s in d["similar"]))
        if d.get("note", {}).get("en"):
            lines.append("Difference:\n" + d["note"]["en"] + "\n" + d["note"]["th"])
        for s in d.get("similar", []):
            if s.get("exam"):
                lines.append(f"Exam pair: {g['name']} ≈ {s['g']} ({s['exam']})")
        # "appears_in" stays in meta, NOT in the text: if the model sees ids it was not given as
        # sources, it copies them as citations (found in testing). Linking uses meta instead.
        chunks.append({"id": f"grammar:{g['name']}", "kind": "grammar", "text": "\n".join(lines),
                       "meta": {"name": g["name"], "reviewed": bool(g.get("reviewed")),
                                "appears_in": sorted(where[g["name"]])}})
    return chunks


def build(rounds=(102, 96, 91)):
    return question_chunks(rounds) + grammar_chunks()


if __name__ == "__main__":
    chunks = build()
    kinds = defaultdict(int)
    for c in chunks:
        kinds[c["kind"]] += 1
    print(dict(kinds), "chunks")
    print(next(c for c in chunks if c["id"] == "96-reading-3")["text"])
