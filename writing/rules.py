"""Writing checker, layers 1 + 2: official rules and language checks (no AI).

Rules come from the official guides (쓰기 답안 작성 방법, 원고지 사용법):
  51–52  one sentence · no words copied from around the ( ) · same formality as the text
  53–54  length in 원고지 cells (53: 200–300, 54: 600–700) · no -ㅂ/습니다 or -아/어요 endings ·
         no spoken expressions · no title · no copying the question (54) · no bullet points
Length = every character including spaces: matches the official counts "(288자)" and "(300자)"
on the model answers of rounds 91 and 102 exactly.

Every issue: {"rule", "layer", "en", "th", "excerpt"}  — messages are short, the excerpt shows where.
"""
import re

from kiwipiepy import Kiwi

LENGTH = {53: (200, 300), 54: (600, 700)}
_kiwi = None

# Spoken / informal expressions (form, Kiwi tag) -> written alternative
SPOKEN = {
    ("근데", "MAJ"): "그런데", ("그니까", "MAJ"): "그러니까", ("너무", "MAG"): "매우 / 상당히",
    ("진짜", "MAG"): "정말 / 매우", ("되게", "MAG"): "매우", ("엄청", "MAG"): "매우 / 상당히",
    ("완전", "MAG"): "매우", ("좀", "MAG"): "조금 / 다소", ("랑", "JKB"): "와/과", ("랑", "JC"): "와/과",
    ("이랑", "JKB"): "와/과", ("이랑", "JC"): "와/과", ("한테", "JKB"): "에게", ("하고", "JC"): "와/과",
    ("거", "NNB"): "것", ("뭐", "NP"): "무엇", ("이거", "NP"): "이것", ("그거", "NP"): "그것",
    ("저거", "NP"): "저것",
}
POLITE_END = re.compile(r"(습니다|ㅂ니다|니다|요|죠)$")


def kiwi():
    global _kiwi
    _kiwi = _kiwi or Kiwi()
    return _kiwi


def issue(rule, en, th, excerpt="", layer="rule"):
    return {"rule": rule, "layer": layer, "en": en, "th": th, "excerpt": excerpt}


def cells(text):
    """Length as TOPIK counts it: every character incl. spaces; paragraph breaks and indents not counted
    (matches the official "(288자)" / "(300자)" on the model answers exactly)."""
    return sum(len(p.strip()) for p in text.strip().split("\n") if p.strip())


def word_at(text, pos):
    """The whole word (between spaces) that contains character position pos."""
    start = max(text.rfind(" ", 0, pos), text.rfind("\n", 0, pos)) + 1
    ends = [i for i in (text.find(" ", pos), text.find("\n", pos)) if i != -1]
    return text[start:min(ends) if ends else len(text)]


def endings(text):
    """Sentence-final endings (EF) with the word they are in, e.g. ('습니다', '증가했습니다.')."""
    return [(t.form, word_at(text, t.start)) for t in kiwi().tokenize(text) if t.tag == "EF"]


def spoken_expressions(text):
    found = []
    for t in kiwi().tokenize(text):
        key = (t.form, t.tag.split("-")[0])
        if key in SPOKEN:
            found.append((t.form, SPOKEN[key], " ".join(text[max(0, t.start - 8):t.start + t.len + 8].split())))
    return found


def check_spoken(text):
    return [issue("spoken", f"Spoken expression '{f}' → use '{alt}' in writing.",
                  f"สำนวนภาษาพูด '{f}' → ในงานเขียนใช้ '{alt}'", ctx, layer="language")
            for f, alt, ctx in spoken_expressions(text)]


def longest_common(a, b):
    """Longest common substring length (spaces removed) — used to detect copying the question."""
    a, b = re.sub(r"\s+", "", a), re.sub(r"\s+", "", b)
    best, prev = (0, ""), [0] * (len(b) + 1)
    for i in range(1, len(a) + 1):
        cur = [0] * (len(b) + 1)
        for j in range(1, len(b) + 1):
            if a[i - 1] == b[j - 1]:
                cur[j] = prev[j - 1] + 1
                if cur[j] > best[0]:
                    best = (cur[j], a[i - cur[j]:i])
        prev = cur
    return best


# ---------- 51–52: fill the blank ----------

def blank_context(text, marker):
    """Words just before and after '( ㉠ )' in the question text."""
    m = re.search(r"([^\s()]*)\s*\(\s*" + marker + r"\s*\)\s*([^\s()]*)", text)
    return (m.group(1), m.group(2)) if m else ("", "")


def text_style(text):
    """'formal' if the passage ends sentences with -ㅂ/습니다, 'plain' if with -다."""
    forms = [f for f, _ in endings(text)]
    formal = sum(bool(re.search(r"니다$", f)) for f in forms)
    plain = sum(f in ("다", "ᆫ다", "는다", "었다") or f.endswith("다") and not f.endswith("니다") for f in forms)
    return "formal" if formal > plain else "plain"


def check_short(question_text, marker, answer):
    out = []
    answer = answer.strip()
    if len(kiwi().split_into_sents(answer)) > 1 or len(re.findall(r"[.?!]", answer.rstrip(".?!"))) > 0:
        out.append(issue("one_sentence", "Write only one sentence for each blank.",
                         "เขียนเพียงหนึ่งประโยคต่อหนึ่งช่องว่าง", answer))
    before, after = blank_context(question_text, marker)
    words = answer.rstrip(".?!").split()
    if before and words and words[0] == before:
        out.append(issue("repeats_context", f"Do not repeat '{before}', which is already before the ( ).",
                         f"ไม่ต้องเขียน '{before}' ซ้ำ เพราะมีอยู่หน้า ( ) แล้ว", answer))
    if after and words and words[-1].rstrip(".?!") == after.rstrip(".?!"):
        out.append(issue("repeats_context", f"Do not repeat '{after}', which is already after the ( ).",
                         f"ไม่ต้องเขียน '{after}' ซ้ำ เพราะมีอยู่หลัง ( ) แล้ว", answer))
    ends = endings(answer)
    if ends:
        style = text_style(question_text)
        form, word = ends[-1]
        if style == "formal" and not re.search(r"(니다|니까)$", form):
            out.append(issue("formality", "The text uses -ㅂ/습니다; end your sentence the same way.",
                             "บทความใช้ -ㅂ/습니다 ให้ลงท้ายประโยคแบบเดียวกัน", word))
        if style == "plain" and POLITE_END.search(form):
            out.append(issue("formality", "The text uses the -다 written style; do not end with -ㅂ/습니다 or -요.",
                             "บทความใช้รูป -다 (ภาษาเขียน) อย่าลงท้ายด้วย -ㅂ/습니다 หรือ -요", word))
    return out + check_spoken(answer)


# ---------- 53–54: essays ----------

def check_essay(number, question_text, answer):
    out = []
    lo, hi = LENGTH[number]
    n = cells(answer)
    if n < lo:
        out.append(issue("too_short", f"{n} characters: write at least {lo} (spaces count).",
                         f"{n} ตัวอักษร: ต้องเขียนอย่างน้อย {lo} ตัว (นับช่องว่างด้วย)"))
    if n > hi:
        out.append(issue("too_long", f"{n} characters: write at most {hi} (spaces count).",
                         f"{n} ตัวอักษร: เขียนได้ไม่เกิน {hi} ตัว (นับช่องว่างด้วย)"))
    polite = [word for form, word in endings(answer) if POLITE_END.search(form)]
    if polite:
        out.append(issue("polite_ending", "Use the -다 written style; -ㅂ/습니다 and -아/어요 lose points.",
                         "ใช้รูป -다 (ภาษาเขียน) ถ้าลงท้ายด้วย -ㅂ/습니다 หรือ -아/어요 จะถูกหักคะแนน",
                         ", ".join(polite[:3])))
    lines = [l.strip() for l in answer.strip().split("\n") if l.strip()]
    if len(lines) > 1 and len(lines[0]) <= 25 and not re.search(r"[.?!]$", lines[0]):
        out.append(issue("title", "Do not write a title.", "ห้ามเขียนชื่อเรื่อง", lines[0]))
    if any(re.match(r"^([-•·*▪○●]|\d+[.)]|[①-⑩])\s*", l) for l in lines):
        out.append(issue("bullets", "Write in full paragraphs, not bullet points.",
                         "เขียนเป็นย่อหน้า ห้ามเขียนเป็นข้อ ๆ"))
    if number == 54:
        length, copied = longest_common(answer, question_text)
        if length >= 20:
            out.append(issue("copied_question", "Do not copy the question; say it in your own words.",
                             "ห้ามลอกโจทย์ ให้เรียบเรียงด้วยคำของตัวเอง", copied[:40]))
    return out + check_spoken(answer)


def check(number, question_text, answer):
    """number: 51–54. For 51/52, answer = {'㉠': '...', '㉡': '...'}; for 53/54 a string."""
    if number in (51, 52):
        out = []
        for marker, text in answer.items():
            for i in check_short(question_text, marker, text):
                out.append({**i, "blank": marker})
        return out
    return check_essay(number, question_text, answer)


# ---------- language layer: spacing (띄어쓰기) ----------

def space_positions(text):
    """Positions (in the text without spaces) where a space follows."""
    out, n = set(), 0
    for ch in text:
        if ch.isspace():
            if n:
                out.add(n)
        else:
            n += 1
    return out


def check_spacing(text):
    """Clear spacing errors only (Kiwi's spacing model + the tested line-joining rules).

    Kiwi also suggests spaces that are optional in Korean (compound nouns 환경보호단체,
    numbers 24조 2천억), which would mark correct answers as wrong. So we report:
      missing  two words written together, unless noun+noun (compound) or next to a digit
      extra    a space before a part that cannot stand alone (공부 를, 했 다)
    """
    from pipeline.structure import is_mid_word
    out = []
    for line in [l for l in text.split("\n") if l.strip()]:
        words = line.split()
        # extra spaces: a space before a dependent piece
        attached = False                                   # previous word was itself a detached piece
        for left, right in zip(words, words[1:]):
            if attached:
                attached = False
                continue
            alone = kiwi().tokenize(right)[:1]
            dependent = alone and alone[0].tag.startswith(("J", "E", "XS"))     # 를, 했다-endings, 하다-suffix
            after_noun = kiwi().tokenize(left)[-1].tag.startswith("NNG")
            if alone and after_noun and alone[0].form in ("하", "되") and alone[0].tag.startswith("VV"):
                dependent = True                                                # 증가 하였다 -> 증가하였다
            optional = re.match(r"^(받|드리|당하|시키)", right) and kiwi().tokenize(left)[-1].tag.startswith("NN")
            if left[-1].isalnum() and right[0].isalnum() and dependent and not optional and is_mid_word(left, right):
                attached = True
                out.append(issue("spacing_extra", f"No space needed: {left}{right}",
                                 f"ไม่ต้องเว้นวรรค: {left}{right}", f"{left} {right}", layer="language"))
        # missing spaces: Kiwi splits one written word into two real words
        for w in words:
            fixed = kiwi().space(w, reset_whitespace=True).split()
            for a, b in zip(fixed, fixed[1:]):
                if a[-1].isdigit() or b[0].isdigit() or not (a[-1].isalnum() and b[0].isalnum()):
                    continue
                tags = [t.tag for t in kiwi().tokenize(a)][-1:] + [t.tag for t in kiwi().tokenize(b)][:1]
                if all(t.startswith(("NN", "NR", "SN", "SL", "XR")) for t in tags):
                    continue                                   # compound noun: spacing optional
                if not tags[0].startswith(("J", "E")):
                    continue                                   # only after a particle / ending is it a sure boundary
                if not is_mid_word(a, b):
                    out.append(issue("spacing_missing", f"Add a space: {a} {b}", f"ควรเว้นวรรค: {a} {b}",
                                     w, layer="language"))
    return out
