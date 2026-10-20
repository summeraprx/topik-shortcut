"""Evaluate "Ask TOPIK" (RAG): retrieval quality and answer quality.

The test set is built AUTOMATICALLY from our own data, so every query has a known right answer:
  meaning     "What does X mean?"                      -> grammar card X
  usage       "Find exam questions that use X"         -> any exam question where Kiwi found X
  difference  "What is the difference between X and Y?" -> BOTH cards X and Y
  paraphrase  "Which grammar means '<meaning>'?"       -> grammar card X   (no grammar name in the query)
  lookup      a sentence pasted from an exam question  -> that exam question (Korean only)
Each query exists in Korean, English and Thai (paraphrase: English and Thai only).

Retrieval metrics (per search mode: bm25 / vector / hybrid):
  hit@1   the first result is correct
  hit@5   a correct result is in the top 5   (difference: both cards in the top 5)
  MRR     mean of 1 / rank of the first correct result (1.0 = always first)

Answer metrics (real model, small sample): valid citations, answer language, latency.

Run:  .venv/bin/python -m eval.eval_rag              (retrieval, ~1 min)
      .venv/bin/python -m eval.eval_rag --answers 12 (+ 12 real answers, slow on a small Mac)
"""
import json
import random
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

from rag.search import INDEX, Searcher, embed

OUT = INDEX / "eval"
# (label, search mode, keyword weight in the fusion)
MODES = (("bm25", "bm25", 1.0), ("vector", "vector", 1.0), ("hybrid 1.0", "hybrid", 1.0),
         ("router", "auto", 1.0), ("router+names", "auto+names", 1.0))
TEMPLATES = {
    "meaning": {"ko": "{x}은/는 무슨 뜻이에요?", "en": "What does {x} mean?", "th": "{x} แปลว่าอะไร"},
    "usage": {"ko": "{x}이/가 쓰인 기출 문제를 찾아 주세요.", "en": "Find exam questions that use {x}.",
              "th": "หาข้อสอบที่ใช้ {x}"},
    "difference": {"ko": "{x}와/과 {y}의 차이가 뭐예요?", "en": "What is the difference between {x} and {y}?",
                   "th": "{x} กับ {y} ต่างกันอย่างไร"},
    "paraphrase": {"en": "Which Korean grammar means '{m}'?", "th": "ไวยากรณ์เกาหลีตัวไหนแปลว่า '{m}'"},
}


def build_testset(searcher):
    cards = {c["meta"]["name"]: c for c in searcher.chunks if c["kind"] == "grammar"}
    labels = {c["meta"]["name"]: c for c in cards.values()}
    meaning_of = {}
    for c in cards.values():
        lines = dict(l.split(": ", 1) for l in c["text"].split("\n")[:3] if ": " in l)
        meaning_of[c["meta"]["name"]] = {"en": lines.get("Meaning", ""), "th": lines.get("ความหมาย", "")}

    tests = []
    for name, card in cards.items():
        gid = card["id"]
        for lang, t in TEMPLATES["meaning"].items():
            tests.append({"type": "meaning", "lang": lang, "query": t.format(x=name), "expected": [gid]})
        if card["meta"]["appears_in"]:
            for lang, t in TEMPLATES["usage"].items():
                tests.append({"type": "usage", "lang": lang, "query": t.format(x=name),
                              "expected": card["meta"]["appears_in"]})
        for lang, t in TEMPLATES["paraphrase"].items():
            tests.append({"type": "paraphrase", "lang": lang, "query": t.format(m=meaning_of[name][lang]),
                          "expected": [gid]})
    # lookup: a learner pastes one sentence of a question (10–60 characters) to find it
    import re
    random.seed(1)
    from collections import Counter
    seen = Counter(x.strip() for c in searcher.chunks if c["kind"] == "question" for x in c["text"].split("\n"))
    for c in searcher.chunks:
        if c["kind"] != "question":
            continue
        body = "\n".join(l for l in c["text"].split("\n")[2:] if seen[l.strip()] == 1)   # skip title, instruction, shared stems
        sentences = [x.strip() for x in re.split(r"(?<=[.?!])\s+|\n", body)
                     if 10 <= len(x.strip()) <= 60 and not x.strip()[0] in "①②③④" and "정답" not in x]
        if sentences:
            tests.append({"type": "lookup", "lang": "ko", "query": random.choice(sentences), "expected": [c["id"]]})
    # difference: each similar pair once, only if both are grammar cards
    pairs = set()
    for name, card in cards.items():
        similar = [l for l in card["text"].split("\n") if l.startswith("Similar: ")]
        for other in (similar[0][9:].split(", ") if similar else []):
            if other in labels:
                pairs.add(tuple(sorted((name, other))))
    for x, y in sorted(pairs):
        for lang, t in TEMPLATES["difference"].items():
            tests.append({"type": "difference", "lang": lang, "query": t.format(x=x, y=y),
                          "expected": [f"grammar:{x}", f"grammar:{y}"], "need_all": True})
    return tests


def score(test, ids):
    """(hit@1, hit@5, reciprocal rank) for one query."""
    expected = set(test["expected"])
    if test.get("need_all"):
        if not ids:
            return 0.0, 0.0, 0.0
        top5 = set(ids[:5])
        found = [i for i, x in enumerate(ids, 1) if x in expected]
        return float(ids[0] in expected), float(expected <= top5), (1 / found[0] if found else 0.0)
    ranks = [i for i, x in enumerate(ids, 1) if x in expected]
    first = ranks[0] if ranks else None
    return float(first == 1), float(first is not None and first <= 5), (1 / first if first else 0.0)


def evaluate_retrieval(searcher, tests):
    vecs = np.vstack([embed([t["query"] for t in tests[i:i + 32]]) for i in range(0, len(tests), 32)])
    rows = defaultdict(lambda: defaultdict(list))      # (mode, group) -> metric -> values
    failures = []
    from rag.answer import with_linked_questions
    for t, v in zip(tests, vecs):
        for mode, search_mode, w in MODES:
            names = search_mode.endswith("+names")
            hits = searcher.search(t["query"], k=20, mode=search_mode.replace("+names", ""), qvec=v,
                                   bm25_weight=w, use_names=names)
            ids = [h["id"] for h in hits]
            if t["type"] == "usage":
                # what the answer step sees: top 5 + exam questions linked from grammar cards
                ids = [h["id"] for h in with_linked_questions(hits[:5], searcher)]
                hit = any(i in t["expected"] for i in ids)
                h1, h5, rr = float(bool(ids) and ids[0] in t["expected"]), float(hit), float(hit)
            else:
                h1, h5, rr = score(t, ids)
            for group in ("ALL", t["type"], f"lang:{t['lang']}"):
                rows[(mode, group)]["hit@1"].append(h1)
                rows[(mode, group)]["hit@5"].append(h5)
                rows[(mode, group)]["mrr"].append(rr)
            if mode == "router+names" and not h5:
                failures.append({**t, "got": ids[:5]})
    return rows, failures


def print_table(rows, tests):
    groups = ["ALL", "meaning", "usage", "difference", "paraphrase", "lookup", "lang:ko", "lang:en", "lang:th"]
    print("usage = with link-following (top 5 + linked exam questions); hit@5 there = found at all")
    print(f"\n{'':12} {'n':>4} " + " ".join(f"{m:>22}" for m, _, _ in MODES))
    print(f"{'':12} {'':>4} " + " ".join(f"{'hit@1  hit@5   MRR':>22}" for _ in MODES))
    for g in groups:
        n = len(rows[("vector", g)]["hit@1"])
        cells = []
        for m, _, _ in MODES:
            r = rows[(m, g)]
            cells.append(f"{100 * np.mean(r['hit@1']):5.1f} {100 * np.mean(r['hit@5']):6.1f} {np.mean(r['mrr']):5.2f}")
        print(f"{g:12} {n:4} " + " ".join(f"{c:>22}" for c in cells))


def evaluate_answers(searcher, tests, n):
    from rag.answer import ask, language
    random.seed(0)
    by_lang = defaultdict(list)
    for t in tests:
        if t["type"] in ("meaning", "usage", "difference"):
            by_lang[t["lang"]].append(t)
    sample = [t for lang in ("ko", "en", "th") for t in random.sample(by_lang[lang], n // 3)]
    results = []
    for i, t in enumerate(sample, 1):
        r = ask(t["query"], searcher)
        r["type"], r["right_language"] = t["type"], language(r["answer"]) == t["lang"]
        results.append(r)
        print(f"  {i:2}/{len(sample)} {t['lang']} {t['type']:10} {r['seconds']:5.1f}s  "
              f"citations {len(r['citations'])}, invalid {len(r['invalid_citations'])}, "
              f"language {'ok' if r['right_language'] else 'WRONG'}")
    cited = sum(len(r["citations"]) for r in results)
    invalid = sum(len(r["invalid_citations"]) for r in results)
    print(f"\nanswers: {len(results)} | with ≥1 citation: {sum(bool(r['citations']) for r in results)}"
          f" | citations: {cited}, invalid: {invalid} ({100 * invalid / max(cited, 1):.1f}%)"
          f" | right language: {sum(r['right_language'] for r in results)}"
          f" | median time: {np.median([r['seconds'] for r in results]):.0f}s")
    return results


def main():
    searcher = Searcher()
    tests = build_testset(searcher)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "testset.json").write_text(json.dumps(tests, ensure_ascii=False, indent=1))
    counts = defaultdict(int)
    for t in tests:
        counts[t["type"]] += 1
    print(f"test set: {len(tests)} queries {dict(counts)}")

    rows, failures = evaluate_retrieval(searcher, tests)
    print_table(rows, tests)
    (OUT / "retrieval_failures.json").write_text(json.dumps(failures, ensure_ascii=False, indent=1))
    print(f"\nrouter+names misses (not in top 5): {len(failures)} -> {OUT / 'retrieval_failures.json'}")

    if "--answers" in sys.argv:
        n = int(sys.argv[sys.argv.index("--answers") + 1])
        results = evaluate_answers(searcher, tests, n)
        (OUT / "answers.json").write_text(json.dumps(results, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
