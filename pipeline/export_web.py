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
VOCAB_TOP = 400


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
    return {
        "rounds": ROUNDS,
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
    rows = load(ANALYSIS / "vocab.json")[:VOCAB_TOP]
    return [{"lemma": r["lemma"], "pos": r["pos"], "count": r["count"], "rounds": r["rounds"],
             "n_questions": r["n_questions"], "where": r["where"], "examples": r["examples"]} for r in rows]


def main():
    questions = [q for r in ROUNDS for q in load(PROCESSED / f"questions_{r}.json")]
    OUT.mkdir(parents=True, exist_ok=True)
    files = {"overview.json": overview(questions), "grammar.json": grammar(), "vocab.json": vocab(),
             "questions.json": [{k: q[k] for k in ("round", "section", "number", "instruction", "shared_passage",
                                                   "text", "choices", "answer", "points", "passage_withheld")}
                                for q in questions]}
    for name, data in files.items():
        (OUT / name).write_text(json.dumps(data, ensure_ascii=False))
        print(f"{name:16} {len(data) if isinstance(data, list) else 'object'}")


if __name__ == "__main__":
    main()
