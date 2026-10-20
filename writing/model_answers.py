"""Official model answers (모범 답안) for Q51–54 -> data/processed/writing_model_answers.json.

Q53/54 essays come from the answer-key OCR (page 2): Q53 ends at the official count "(NNN자)",
Q54 is the rest. Printed lines are joined with the tested line-joining rule (mid-word or not).
Q51/52 short answers (first of the official alternatives) were read from the same pages.
Run: .venv/bin/python -m writing.model_answers
"""
import json
import re
from pathlib import Path

from pipeline.structure import is_mid_word

ROOT = Path(__file__).resolve().parent.parent
OCR = ROOT / "data" / "ocr"
OUT = ROOT / "data" / "processed" / "writing_model_answers.json"
SHORT = {
    102: {51: {"㉠": "(removed)", "㉡": "(removed)"}, 52: {"㉠": "(removed)", "㉡": "(removed)"}},
    96: {51: {"㉠": "(removed)", "㉡": "(removed)"}, 52: {"㉠": "(removed)", "㉡": "(removed)"}},
    91: {51: {"㉠": "(removed)", "㉡": "(removed)"}, 52: {"㉠": "(removed)", "㉡": "(removed)"}},
}
MARKERS = {"51", "52", "53", "54", "10", "30", "50"}


def join(lines):
    """lines: [(text, right_edge)]. A line that stops well before the right edge ends a paragraph."""
    full = max(r for _, r in lines)
    text, prev_right = "", full
    for line, right in lines:
        if not text:
            text = line
        elif prev_right < full - 0.05 and text.endswith("."):
            text += "\n" + line
        else:
            text += ("" if is_mid_word(text.split()[-1], line.split()[0]) else " ") + line
        prev_right = right
    return text


def essays(rnd):
    page = sorted(OCR.glob(f"*{rnd}회_정답*"))[0] / "page_002.json"
    rows = sorted(json.loads(page.read_text()), key=lambda l: (round(l["y"], 3), l["x"]))
    def is_essay_line(t):
        # skip header, scores, and the Q51/52 short answers (㉠/㉡ read as ⑦, L, ©; "/" between alternatives)
        return (t not in MARKERS and len(t) > 12 and "/" not in t and not re.match(r"^[⑦L©㉠㉡]\s", t)
                and not any(w in t for w in ("모범답안", "수준", "영역")))
    lines = [(r["text"].strip(), r["x"] + r["w"]) for r in rows if r["x"] > 0.15 and is_essay_line(r["text"].strip())]
    end53 = next(i for i, (l, _) in enumerate(lines) if re.search(r"\d+자\)", l))
    q53 = re.sub(r"\s*\(?\d+자\)\s*$", "", join(lines[:end53 + 1]))
    q54 = re.sub(r"\s*\(?\d+자\)\s*$", "", join(lines[end53 + 1:]))
    official = int(re.search(r"(\d+)자\)", lines[end53][0]).group(1))
    return q53, q54, official


def main():
    out = {}
    for rnd, short in SHORT.items():
        q53, q54, official = essays(rnd)
        out[str(rnd)] = {"51": short[51], "52": short[52], "53": q53, "54": q54, "53_official_count": official}
        print(f"round {rnd}: 53 = {len(q53)} chars (official {official}) | 54 = {len(q54)} chars")
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
