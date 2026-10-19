"""Step 3 of the pipeline: turn OCR lines into structured questions.

Input:  data/ocr/<booklet>/page_*.json   (from ocr.py)
        data/processed/answer_keys.json  (from answer_keys.py)
Output: data/processed/questions_<round>.json
        data/processed/structure_report.txt   (validation: what looks wrong, for human check)

Layout rules (from looking at the real OCR output):
  - Instruction:     "※ [5~8] 다음은 ..." at the left margin. Applies to a group of questions.
  - Shared passage:  text between an instruction and its first question (e.g. [46~47] 다음을 읽고 ...).
  - Question start:  "5." at the left margin (x < 0.17). Text after it = question text.
  - Choices:         4 per question, in reading order = ① ② ③ ④. OCR often misreads the
                     circled number (① -> "l" or "1"), so we trust ORDER, not the symbol.
Run:    .venv/bin/python pipeline/structure.py 102 96 91
"""
import json
import re
import sys
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parent.parent
OCR = ROOT / "data" / "ocr"
OUT = ROOT / "data" / "processed"

LEFT_MARGIN = 0.17          # question numbers / instructions start left of this
ROW_TOLERANCE = 0.008       # lines whose y differs less than this are on the same row
INSTRUCTION = re.compile(r"^※\s*\[\s*(\d+)\s*[~∼\-]\s*(\d*)")
QUESTION_NO = re.compile(r"^([\dyl기IOo]{1,2})\s*\.(?:\s+|$)")   # letters = common OCR misreads of digits
# A choice line starts with a circled number, or a common misread of ① ("l", "I", "|", "1 ")
CHOICE_START = re.compile(r"^(?:[①②③④]|[lI|](?=\s)|1(?=\s+\D)|\(1\))\s*")
CHOICE_SPLIT = re.compile(r"\s*[①②③④]\s*")
POINTS = re.compile(r"각\s*(\d)\s*점")


class Question(BaseModel):
    """One exam question. Pydantic checks types and ranges when the object is created."""
    round: int = Field(ge=35)                       # only TOPIK II format, round 35+
    section: Literal["reading", "listening_writing", "writing"]
    number: int = Field(ge=1, le=54)
    instruction: str = ""
    shared_passage: str = ""
    text: str = ""
    choices: list[str] = []
    answer: int | None = Field(default=None, ge=1, le=4)
    points: int | None = None
    pages: list[int] = []
    warnings: list[str] = []
    resolved: list[str] = []      # warnings fixed by a human correction (kept as history)
    corrected: list[str] = []     # fields replaced from data/corrections/<round>.json
    regions: list[tuple[int, float, float]] = []   # (page, y_top, y_bottom) where it is printed
    instruction_region: tuple[int, float, float] | None = None   # where the ※ instruction line is


def find_booklet(rnd, section):
    pattern = {"reading": "*{r}회*읽기*", "listening_writing": "*{r}회*듣기,쓰기*"}[section]
    dirs = sorted(OCR.glob(pattern.format(r=rnd)))
    if len(dirs) != 1:
        raise FileNotFoundError(f"round {rnd} {section}: expected 1 booklet, found {len(dirs)}")
    return dirs[0]


def load_lines(booklet, start=None, stop=None):
    """All lines of a booklet in reading order, without page header/footer.

    start/stop: regex of the line where the section begins / ends (stop line excluded).
    Default start = first "※ [" instruction (skips cover and instruction pages).
    """
    lines = []
    for page_file in sorted(booklet.glob("page_*.json")):
        page = int(page_file.stem.split("_")[1])
        for l in json.loads(page_file.read_text()):
            if l["y"] < 0.075:                                        # page header
                continue
            if l["y"] > 0.9 and re.fullmatch(r"\d{1,2}", l["text"]):  # page number
                continue
            lines.append({**l, "page": page})
    lines.sort(key=lambda l: (l["page"], l["y"], l["x"]))
    first = next(i for i, l in enumerate(lines)
                 if (re.search(start, l["text"]) if start else INSTRUCTION.match(l["text"])))
    last = next((i for i, l in enumerate(lines) if stop and i > first and re.search(stop, l["text"])),
                len(lines))
    return lines[first:last]


def is_choice(line):
    return line["x"] < 0.75 and bool(CHOICE_START.match(line["text"]))


def split_choices(text):
    """'l 예매 방법 ② 행사 소개 ③ 등록 문의' -> ['예매 방법', '행사 소개', '등록 문의']"""
    text = CHOICE_START.sub("", text, count=1)
    return [p.strip() for p in CHOICE_SPLIT.split(text) if p.strip()]


def join_row(parts):
    """Join OCR pieces of one row: '새긴 후 (' + ') 순서대로' -> '새긴 후 ( ) 순서대로'"""
    return " ".join(p["text"] for p in sorted(parts, key=lambda p: p["x"]))


WRAP_EDGE = 0.80   # wrapped passage lines end at x ≈ 0.84; shorter lines are real line breaks
_kiwi = None
JOIN_LOG = []


def is_mid_word(left, right):
    """Was this line break in the middle of a word? Decided from Kiwi's morphemes.

    Rules (tested on 27 real cases, see LEARNING_LOG):
      1. Never join after . ! ? ) or before ( •          -> 과일이다. | (다)
      2. Next line starts with a particle / ending / suffix / -어지다  -> join   (겨울|에는, 발달|하였다)
      3. Left is already a complete word (ends with particle or 은/는/ㄹ-type ending) -> space (산성이|중화)
      4. Break falls inside one morpheme                    -> join   (흥미|진진한, 천문|학자)
    """
    global _kiwi
    if _kiwi is None:
        from kiwipiepy import Kiwi
        _kiwi = Kiwi()
    if left[-1] in ".!?)』」》:" or right[0] in "(《『「•※" or left[-1].isdigit() or right[0].isdigit():
        return False
    b = len(left)
    tokens = _kiwi.tokenize(left + right)
    at_b = [t for t in tokens if t.start == b]
    last = _kiwi.tokenize(left)[-1].tag
    after_noun = last.startswith(("N", "XR", "XSN", "J", "SL", "SH"))
    if at_b:
        tag = at_b[0].tag
        # particles, 이다 and suffixes only attach to nouns: '해 | 의학', '두고 | 이를' are NOT joined
        if tag.startswith(("J", "VCP", "XS")) and after_noun:
            return True
        if tag.startswith("E") or (tag == "VX" and at_b[0].form == "지"):
            return True
    spanning = [t for t in tokens if t.start < b < t.start + t.len]
    if spanning and spanning[0].tag.startswith("E"):
        return True                                  # an ending crosses the break: 높아지는|지를
    if last.startswith("J") or last == "ETM":
        return False
    if not spanning:
        return False
    # Left is a conjugated verb (해, 떨어): join only if the result is one verb (떨어뜨리다)
    if last.startswith("E"):
        return spanning[0].tag in ("VV", "VA")
    return True


def join_lines(prev, new, prev_right):
    """Add a printed line to text. Exam text wraps lines in the middle of words
    ('이루어 / 진다'), so wrapped lines are joined with or without a space by is_mid_word()."""
    if not prev:
        return new
    if prev_right < WRAP_EDGE:
        return prev + "\n" + new
    words = new.split()
    left, right = prev.split()[-1], words[0]
    following = words[1] if len(words) > 1 else ""
    # '-는 데 있다 / 데에 / 데가' = noun 데 (needs space); looks identical to the ending -는데
    if right in ("데에", "데가", "데도", "데는") or (right == "데" and following.startswith("있")):
        join = False
    else:
        join = is_mid_word(left, right)
    JOIN_LOG.append(f"{'JOIN ' if join else 'space'}  {left} | {right}")
    return prev + ("" if join else " ") + new


def rows_of(lines):
    """Group non-choice lines into rows (same page, similar y)."""
    rows, current = [], []
    for l in lines:
        if current and (l["page"] != current[0]["page"] or abs(l["y"] - current[0]["y"]) > ROW_TOLERANCE):
            rows.append(current)
            current = []
        current.append(l)
    if current:
        rows.append(current)
    return rows


def structure(rnd, section, first_q, last_q):
    if section == "listening_writing":   # v1: Writing part only (last pages of booklet 1)
        lines = load_lines(find_booklet(rnd, section), start=r"쓰기\s*\(\s*51", stop=r"원고지 쓰기의 예")
    else:
        lines = load_lines(find_booklet(rnd, section))
    has_choices = section == "reading"
    questions, q = [], None
    instruction, points, passage, expected = "", None, [], first_q
    prev_right, row_right = 0.0, 0.0
    instruction_span = None
    pending = []   # positions of instruction + passage rows, shared by the next question(s)

    for row in rows_of(lines):
        row.sort(key=lambda l: l["x"])
        head = row[0]
        text = join_row(row)
        prev_right, row_right = row_right, max(l["x"] + l["w"] for l in row)
        span = (head["page"], min(l["y"] for l in row), max(l["y"] + l["h"] for l in row))

        # 1) Instruction line starts a new group
        if head["x"] < LEFT_MARGIN and text.startswith("※") and expected:
            instruction, instruction_span = repair_instruction(text, expected), span
            if instruction != text:
                INSTRUCTION_FIXES.append(f"{text[:20]}  ->  {instruction[:20]}")
            m = POINTS.search(text)
            points = int(m.group(1)) if m else None
            passage, q = [], None
            pending = []      # instruction itself is not part of the crop
            continue

        # 2) Question number starts a new question
        m = QUESTION_NO.match(head["text"])
        # A misread letter (e.g. "y." for 7 or 9) is accepted as the expected next number
        number = m and (m.group(1) if m.group(1).isdigit() else str(expected))
        if head["x"] < LEFT_MARGIN and number and int(number) == expected:
            if not in_range(instruction, expected):   # e.g. Q53 has no ※ line of its own
                instruction, points, passage = "", None, []
                instruction_span = None
                pending = []
            q = Question(round=rnd, section=section, number=expected, instruction=instruction,
                         shared_passage="\n".join(passage), points=points)
            q.pages.append(head["page"])
            q.regions = pending + [span]
            q.instruction_region = instruction_span if instruction else None
            if number != m.group(1):
                q.warnings.append(f"number read as '{m.group(1)}'")
            rest = QUESTION_NO.sub("", text, count=1).strip()
            if rest:
                q.text = rest
            questions.append(q)
            expected = expected + 1 if expected < last_q else None
            continue

        # 3) Choice row: if any piece is a choice, every piece in the row is a choice
        #    (OCR sometimes drops the ① symbol entirely, e.g. "(나)-(라)-(가)-(다)")
        if has_choices and any(is_choice(l) for l in row) and expected and (q is None or len(q.choices) >= 4):
            # Choices but no open question: OCR missed the number -> implied question
            q = Question(round=rnd, section=section, number=expected, instruction=instruction, points=points,
                         text="\n".join(passage), warnings=["number not found by OCR (implied)"])
            q.pages.append(head["page"])
            q.regions = pending + [span]
            q.instruction_region = instruction_span if instruction else None
            questions.append(q)
            passage, pending = [], []
            expected = expected + 1 if expected < last_q else None
        if has_choices and q is not None and any(is_choice(l) for l in row):
            for part in row:
                q.choices += split_choices(part["text"])
            q.regions.append(span)
            continue

        # 4) Plain text: question text if inside a question (before choices), else shared passage
        if q is not None and not q.choices:
            q.text = join_lines(q.text, text, prev_right)
            q.regions.append(span)
        elif q is not None and q.choices:
            passage = [text]          # text after a finished question = next passage
            pending = [span]
            q = None
        else:
            passage = [join_lines("\n".join(passage), text, prev_right)]
            pending.append(span)

    for q in questions:
        if section == "listening_writing":
            q.section = "writing"
        fix_choices(q)
        q.regions = merge_regions(q.regions)
    return questions


def merge_regions(spans):
    """Row positions -> one (page, top, bottom) box per page."""
    pages = {}
    for page, top, bottom in spans:
        t, b = pages.get(page, (top, bottom))
        pages[page] = (min(t, top), max(b, bottom))
    return [(p, round(t, 4), round(b, 4)) for p, (t, b) in sorted(pages.items())]


INSTRUCTION_FIXES = []
RAW_RANGE = re.compile(r"^※\s*[\[(]?\s*(\d+)\s*[~∼\-]\s*(\d*)\s*([\]1l기)]?)\s*(.*)", re.S)


def repair_instruction(text, expected):
    """OCR misreads the brackets of "※ [9~12]": "[" -> "1" (※ 19~12]), "]" -> "1" (128~311),
    "7]" -> "기" ([46~4기). The range must contain the current question, which tells us the right reading."""
    m = RAW_RANGE.match(text)
    if not m:
        return text
    lo_raw, hi_raw, closing, rest = m.groups()
    lo_options = [int(lo_raw)] + ([int(lo_raw[1:])] if lo_raw.startswith("1") and len(lo_raw) > 1 else [])
    lo_options = [v for v in lo_options if v <= expected]
    if not lo_options:
        return text
    lo = max(lo_options)
    if closing == "기":
        hi_raw += "7"
    if len(hi_raw) == 3 and hi_raw.endswith("1"):
        hi_raw = hi_raw[:2]
    if not hi_raw or int(hi_raw) < max(lo, expected):
        return text
    return f"※ [{lo}~{int(hi_raw)}] {rest}".strip()


def in_range(instruction, number):
    """Does '※ [51~52] ...' cover this question number?"""
    m = INSTRUCTION.match(instruction)
    if not m:
        return False
    lo, hi = int(m.group(1)), int(m.group(2) or m.group(1))
    if hi < lo:            # OCR damaged the range, e.g. "[46~4기" -> can't tell, keep the group
        return number >= lo
    return lo <= number <= hi


BLANK = re.compile(r"\(\s*[^()\s가-힣0-9]{0,2}\s*\)|\(\s+[0-9]\s*\)|\(\s*[0-9]\s+\)")  # "( )", "( ⑦ )", "(@ )", "( 7)" — not "(금)", "(2)"
MARKERS = "㉠㉡㉢㉣"


def number_blanks(text, count):
    """'( ⑦ ) ... ( ) ... ( C )' -> '( ㉠ ) ... ( ㉡ ) ... ( ㉢ )' (OCR misreads the markers)."""
    if len(BLANK.findall(text)) != count:
        return text, False
    markers = iter(MARKERS[:count])
    return BLANK.sub(lambda _: f"( {next(markers)} )", text), True


def fix_markers(q):
    """Questions whose blanks are labelled ㉠ ㉡ (Writing 51–52) or ㉠–㉣ (Reading 39–41)."""
    if q.section == "writing" and q.number in (51, 52):
        q.text, ok = number_blanks(q.text, 2)
        # instruction "다음 글의 ㉠과 ㉡에 ..." loses the markers in OCR ("다음 글의 과 C에")
        q.instruction = re.sub(r"다음 글의\s*\S{0,2}과\s*\S{0,2}에", "다음 글의 ㉠과 ㉡에", q.instruction)
    elif q.section == "reading" and "들어갈 곳" in q.instruction:
        q.text, ok = number_blanks(q.text, 4)
    else:
        return
    if not ok:
        q.warnings.append("could not label blanks ㉠ ㉡ … (count mismatch)")


def fix_choices(q):
    """Known layout cases where OCR choices need correcting."""
    fix_markers(q)
    if q.section != "reading":
        return
    # Insert-the-sentence questions: choices are always the markers ㉠ ㉡ ㉢ ㉣ (OCR reads them as junk)
    if "들어갈 곳" in q.instruction:
        q.choices = ["㉠", "㉡", "㉢", "㉣"]
    # A notice inside the question can have its own ① ② list. Answer choices always come
    # last, so extra leading "choices" belong to the question text.
    elif len(q.choices) > 4:
        extra, q.choices = q.choices[:-4], q.choices[-4:]
        q.text = (q.text + "\n" + "\n".join(extra)).strip()
        q.warnings.append(f"moved {len(extra)} numbered lines from choices to text")


CORRECTIONS = ROOT / "data" / "corrections"
CORRECTABLE = {"instruction", "shared_passage", "text", "choices"}


def apply_corrections(rnd, questions):
    """Human fixes (read from page images) override OCR. Kept in a file so re-runs keep them."""
    path = CORRECTIONS / f"{rnd}.json"
    if not path.exists():
        return
    fixes = json.loads(path.read_text())
    for q in questions:
        fix = fixes.get(q.section, {}).get(str(q.number))
        if not fix:
            continue
        for key, value in fix.items():
            if key in CORRECTABLE:
                setattr(q, key, value)
                q.corrected.append(key)
        q.resolved, q.warnings = q.warnings, []


def validate(questions, first_q, last_q, answers, needs_choices):
    found = {q.number for q in questions}
    problems = [f"missing question {n}" for n in range(first_q, last_q + 1) if n not in found]
    for q in questions:
        if needs_choices and len(q.choices) != 4:
            q.warnings.append(f"{len(q.choices)} choices (expected 4)")
        if answers:
            q.answer = answers[q.number - 1]
        if needs_choices and q.answer is None:
            q.warnings.append("no answer")
    return problems


def main(rounds):
    keys = json.loads((OUT / "answer_keys.json").read_text())
    report = []
    for rnd in rounds:
        reading = structure(rnd, "reading", 1, 50)
        writing = structure(rnd, "listening_writing", 51, 54)
        apply_corrections(rnd, reading + writing)
        r_problems = validate(reading, 1, 50, keys.get(str(rnd), {}).get("reading"), True)
        w_problems = validate(writing, 51, 54, None, False)

        all_q = reading + writing
        (OUT / f"questions_{rnd}.json").write_text(
            json.dumps([q.model_dump() for q in all_q], ensure_ascii=False, indent=1))
        ok = sum(1 for q in reading if not q.warnings)
        report.append(f"== round {rnd}: reading {len(reading)}/50 found, {ok} clean | writing {len(writing)}/4 found")
        report += [f"  {p}" for p in r_problems + w_problems]
        report += [f"  Q{q.number}: {'; '.join(q.warnings)}" for q in all_q if q.warnings]
        report += [f"  Q{q.number}: corrected {q.corrected} (was: {'; '.join(q.resolved)})"
                   for q in all_q if q.corrected]

    (OUT / "structure_report.txt").write_text("\n".join(report) + "\n")
    (OUT / "line_joins.txt").write_text("\n".join(JOIN_LOG) + "\n")
    (OUT / "instruction_fixes.txt").write_text("\n".join(INSTRUCTION_FIXES) + "\n")
    print("\n".join(report))


if __name__ == "__main__":
    main([int(r) for r in sys.argv[1:]] or [102, 96, 91])
