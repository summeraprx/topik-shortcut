"""Evaluate the extraction pipeline against a hand-checked gold file.

Gold file: data/gold/<round>.json  (made with data/review/review_<round>.html)
Shape of the gold file:
    {
      "round": 102,
      "questions": {
        "reading-1": {
          "text":    {"status": "ok",  "extracted": "...", "gold": "..."},
          "choices": {"status": "ok",  "extracted": ["..", "..", "..", ".."], "gold": [...]},
          ...
        },
        "reading-13": {
          "text":    {"status": "bad", "extracted": "...", "gold": "<your corrected text>"}
        }
      }
    }

For every field we report:
  - strict:      extracted == gold exactly
  - normalized:  equal after removing ALL whitespace (spaces, line breaks)
                 -> separates "formatting" errors from real "content" errors
  - CER:         character error rate = edit distance / number of gold characters
                 (the standard OCR metric; 0% = perfect)

Run:  .venv/bin/python eval/eval_extraction.py 102

Expected shape of the output (numbers are yours to find!):

    field            n   strict   normalized      CER
    instruction     19   xx.x%      xx.x%       x.xx%
    shared_passage   8   ...
    text            54   ...
    choices         50   ...
    ALL            131   ...

Self-check: choices should be 50/50 strict (you marked all choices correct).
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GOLD = ROOT / "data" / "gold"


def as_text(value):
    if value is None:
        return ""
    if isinstance(value, list):
        return "\n".join(value)
    return value


def normalize(text):
    return "".join(text.split())


def edit_distance(a, b):
    previous = list(range(len(b)+1))
    for i, char_a in enumerate(a, 1):
        current = [i]
        for j, char_b in enumerate(b, 1):
            cost = 0 if char_a == char_b else 1
            current.append(min(previous[j] + 1,
                               current[j - 1] + 1,
                               previous[j - 1] + cost))
        previous = current
    return previous[-1]


def evaluate(round_no):
    gold = json.loads((GOLD / f"{round_no}.json").read_text())

    # One row of counters per field name, e.g. stats["text"] = {"n": 0, "strict": 0, ...}
    stats = {}

    for question_id, fields in gold["questions"].items():
        for field, entry in fields.items():
            if entry["status"] == "unchecked":
                continue

            extracted = as_text(entry["extracted"])
            correct = as_text(entry["gold"])

            s = stats.setdefault(field, {"n":0, "strict": 0, "normalized": 0,
                                         "errors": 0, "chars":0})
            
            s["n"] += 1
            s["strict"] += extracted == correct
            s["normalized"] += normalize(extracted) == normalize(correct)
            s["errors"] += edit_distance(normalize(extracted), normalize(correct))
            s["chars"] += len(normalize(correct))

    return stats


def print_table(stats):
    total = {"n": 0, "strict": 0, "normalized":0, "errors":0, "chars":0}
    for s in stats.values():
      for key in total:
        total[key] += s[key]
    stats["ALL"] = total    

    print(f"{'field':15} {'n':>4} {'strict':>8} {'normalized':>11} {'CER':>8}")
    for field, s in stats.items():
        strict = 100 * s["strict"] / s["n"]
        normalized = 100 * s["normalized"] / s["n"]
        cer =  100 * s["errors"] / s["chars"]
        print(f"{field:15} {s['n']:4} {strict:7.1f}% {normalized:10.1f}% {cer:7.2f}%")


if __name__ == "__main__":
    round_no = int(sys.argv[1]) if len(sys.argv) > 1 else 102
    print_table(evaluate(round_no))
