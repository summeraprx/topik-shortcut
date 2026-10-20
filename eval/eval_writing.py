"""Evaluate the Writing checker with error injection.

Clean texts = official model answers (rounds 102, 96, 91; Q51–54). They should get NO issues.
Then one known error is injected at a time, and we check that the right rule fires:

  53/54  polite_ending · spoken · title · bullets · too_short · too_long · copied_question (54) ·
         spacing_missing · spacing_extra · typo (AI layer)
  51/52  one_sentence · repeats_context · formality

Metrics
  detection   share of injected errors where the expected rule fired
  false alarm issues reported on the clean official answers (should be 0)
  AI layer    typo found at the injected spot / issues invented on clean answers (slow; --ai)

Run:  .venv/bin/python -m eval.eval_writing          (rules + language, seconds)
      .venv/bin/python -m eval.eval_writing --ai     (+ local model, a few minutes)
"""
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

from writing.rules import LENGTH, check, check_spacing

ROOT = Path(__file__).resolve().parent.parent
ANSWERS = ROOT / "data" / "processed" / "writing_model_answers.json"
OUT = ROOT / "data" / "processed" / "writing_eval.json"

POLITE = [("였다.", "였습니다."), ("었다.", "었습니다."), ("았다.", "았습니다."), ("있다.", "있습니다."),
          ("이다.", "입니다."), ("한다.", "합니다."), ("된다.", "됩니다."), ("없다.", "없습니다.")]
TYPOS = [("됐다", "됬다"), ("되었다", "되엇다"), ("했다", "햇다"), ("있었다", "있엇다"), ("않", "안"),
         ("것이다", "거시다"), ("때문이다", "때문이다다"), ("증가", "증과"), ("필요", "필료")]


def sentences(text):
    return re.split(r"(?<=다\.)\s+", text)


def inject_essay(number, text, question):
    """Yield (expected_rule, broken_text, injected_piece)."""
    lo, hi = LENGTH[number]
    for old, new in POLITE:
        if old in text:
            yield "polite_ending", text.replace(old, new, 1), new
            break
    s = sentences(text)
    if len(s) > 1:
        yield "spoken", " ".join(s[:1] + ["근데 " + s[1]] + s[2:]), "근데"
    yield "title", "디지털 사회의 변화\n" + text, "title"
    yield "bullets", "- " + text.replace("\n", "\n- "), "- "
    cut = text[:lo - 40]
    yield "too_short", cut[:cut.rfind(".") + 1] or cut, "short"
    longer = text
    while len(longer.replace("\n", "")) <= hi:
        longer += " " + s[-1]
    yield "too_long", longer, "long"
    if number == 54:
        topic = [x for x in re.split(r"(?<=\.)\s+|\n", question)
                 if len(x) > 30 and not re.search(r"(쓰시오|마시오|\d+점)", x)]           # topic text, not instructions
        yield "copied_question", topic[0] + " " + text, topic[0][:20]
    # spacing: glue two words at a clear word boundary / split a word before its ending
    words = text.split(" ")
    for i in range(1, len(words) - 1):
        a, b = words[i], words[i + 1]
        if re.search(r"(을|를|이|가|은|는)$", a) and re.match(r"^[가-힣]+(다|했다|한다)\.?$", b):
            yield "spacing_missing", " ".join(words[:i] + [a + b] + words[i + 2:]), a + b
            break
    for i, w in enumerate(words):
        m = re.match(r"^([가-힣]{2,})(했다|하였다|된다|했기)(\.?)$", w)
        if m:
            yield "spacing_extra", " ".join(words[:i] + [m.group(1) + " " + m.group(2) + m.group(3)] + words[i + 1:]), w
            break


def inject_short(question, answer):
    """answer: {'㉠': ..., '㉡': ...}. Errors go into ㉠."""
    a = answer["㉠"]
    yield "one_sentence", {**answer, "㉠": a.rstrip(".") + ". 그리고 연락해 주세요."}, "two sentences"
    before = re.search(r"([^\s()]+)\s*\(\s*㉠", question)
    if before:
        yield "repeats_context", {**answer, "㉠": before.group(1) + " " + a}, before.group(1)
    if re.search(r"(습|합|됩|입)니다$", a):                                   # not 아니다
        yield "formality", {**answer, "㉠": re.sub(r"(합|됩|입|습)니다$", "한다", a)}, "plain ending"
    elif a.endswith("다"):
        yield "formality", {**answer, "㉠": a[:-1] + "습니다"}, "formal ending"


def main():
    answers = json.loads(ANSWERS.read_text())
    detected, total = defaultdict(int), defaultdict(int)
    false_alarms, misses = [], []
    for rnd, model in answers.items():
        qs = {q["number"]: q for q in json.loads((ROOT / "data" / "processed" / f"questions_{rnd}.json").read_text())
              if q["section"] == "writing"}
        for number in (51, 52, 53, 54):
            question = qs[number]["text"]
            clean = model[str(number)]
            issues = check(number, question, clean)
            if number in (53, 54):
                issues += check_spacing(clean)
            false_alarms += [{"round": rnd, "q": number, **i} for i in issues]
            injected = inject_short(question, clean) if number in (51, 52) else inject_essay(number, clean, question)
            for rule, broken, piece in injected:
                found = check(number, question, broken)
                if number in (53, 54):
                    found += check_spacing(broken)
                total[rule] += 1
                if any(i["rule"] == rule for i in found):
                    detected[rule] += 1
                else:
                    misses.append({"round": rnd, "q": number, "rule": rule, "piece": piece,
                                   "got": [i["rule"] for i in found]})

    print(f"{'injected error':18} {'detected':>9}")
    for rule in total:
        print(f"{rule:18} {detected[rule]:>4} / {total[rule]:<3}")
    n_det, n_tot = sum(detected.values()), sum(total.values())
    print(f"{'ALL':18} {n_det:>4} / {n_tot:<3} = {100 * n_det / n_tot:.1f}%")
    print(f"\nfalse alarms on 12 clean official answers: {len(false_alarms)}")
    for f in false_alarms:
        print(f"   round {f['round']} Q{f['q']}: {f['rule']} | {f['excerpt'][:40]}")
    for m in misses:
        print(f"   MISSED round {m['round']} Q{m['q']} {m['rule']} ({m['piece'][:20]}) got {m['got']}")

    result = {"detected": dict(detected), "total": dict(total), "false_alarms": false_alarms, "misses": misses}
    if "--ai" in sys.argv:
        result["ai"] = evaluate_ai(answers)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=1))


def evaluate_ai(answers):
    """Typo detection by the local model: one typo per essay; plus invented issues on clean essays."""
    from writing.ai import find_errors
    rows = []
    for rnd, model in answers.items():
        for number in ("53", "54"):
            clean = model[number]
            kept, dropped = find_errors(clean)
            rows.append({"round": rnd, "q": number, "kind": "clean", "reported": len(kept), "dropped": len(dropped),
                         "items": [k["en"] for k in kept]})
            for right, wrong in TYPOS:
                if right in clean:
                    broken = clean.replace(right, wrong, 1)
                    kept, dropped = find_errors(broken)
                    hit = any(wrong in k["excerpt"] or k["excerpt"] in broken[broken.find(wrong) - 5:broken.find(wrong) + 10]
                              for k in kept)
                    rows.append({"round": rnd, "q": number, "kind": "typo", "typo": wrong, "found": hit,
                                 "reported": len(kept), "dropped": len(dropped), "items": [k["en"] for k in kept]})
                    break
            print(f"   AI round {rnd} Q{number}: clean -> {rows[-2]['reported']} reported | "
                  f"typo '{rows[-1].get('typo')}' -> {'found' if rows[-1].get('found') else 'MISSED'}")
    typos = [r for r in rows if r["kind"] == "typo"]
    clean = [r for r in rows if r["kind"] == "clean"]
    print(f"\nAI: typos found {sum(r['found'] for r in typos)} / {len(typos)} | "
          f"issues reported on clean answers: {sum(r['reported'] for r in clean)} "
          f"| invented & dropped by the safety check: {sum(r['dropped'] for r in rows)}")
    return rows


if __name__ == "__main__":
    main()
