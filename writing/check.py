"""Writing checker: all three layers for one answer.

  1. rules     official TOPIK rules (length, endings, title, copying, one sentence, formality…)
  2. language  spacing (clear errors only) and spoken expressions
  3. content   nonsense (loose ㅁㄴㅇㄹ, not Korean, repeated sentences) and topic (key items missing)
  4. ai        spelling / grammar, local model; shown as "possible" errors (it finds well, fixes less well)

Run:  .venv/bin/python -m writing.check 102 54 my_answer.txt          (53/54: text file)
      .venv/bin/python -m writing.check 102 51 "㉠ (removed)" "㉡ (removed)"
      add --no-ai to skip the slow model
"""
import json
import re
import sys
from pathlib import Path

from writing.content import check_nonsense, check_topic
from writing.rules import cells, check, check_spacing

ROOT = Path(__file__).resolve().parent.parent
LAYER_TITLE = {"rule": "Official rules", "language": "Language", "content": "Content", "ai": "AI (possible errors)"}


def question(rnd, number):
    qs = json.loads((ROOT / "data" / "processed" / f"questions_{rnd}.json").read_text())
    return next(q for q in qs if q["section"] == "writing" and q["number"] == number)


def run(rnd, number, answer, use_ai=True):
    q = question(rnd, number)
    issues = check(number, q["text"], answer)
    if number in (53, 54):
        issues += check_spacing(answer) + check_nonsense(answer) + check_topic(rnd, number, answer)
        if use_ai:
            from writing.ai import find_errors
            # guard: the model sometimes "corrects" into -ㅂ/습니다 / -요, which the TOPIK rules forbid in 53/54
            issues += [i for i in find_errors(answer)[0] if not re.search(r"([습합됩입]니다|요)\.?$", i["correction"])]
    return issues


def main(args):
    use_ai = "--no-ai" not in args
    args = [a for a in args if a != "--no-ai"]
    rnd, number = int(args[0]), int(args[1])
    if number in (51, 52):
        answer = {a.split(" ", 1)[0]: a.split(" ", 1)[1] for a in args[2:]}
    else:
        answer = Path(args[2]).read_text()
        print(f"Length: {cells(answer)} characters (spaces count)\n")
    issues = run(rnd, number, answer, use_ai)
    if not issues:
        print("No issues found. / ไม่พบข้อผิดพลาด")
    for layer in ("rule", "language", "content", "ai"):
        found = [i for i in issues if i["layer"] == layer]
        if found:
            print(f"== {LAYER_TITLE[layer]} ({len(found)})")
            for i in found:
                blank = f"[{i['blank']}] " if i.get("blank") else ""
                print(f"  • {blank}{i['en']}\n    {i['th']}")


if __name__ == "__main__":
    main(sys.argv[1:])
