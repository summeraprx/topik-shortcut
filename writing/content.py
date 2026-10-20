"""Writing checker, content layer (no AI): is the answer real Korean, and is it about the question?

  nonsense  loose consonants/vowels (ㅁㄴㅇㄹ), mostly non-Korean text, the same sentence repeated
  topic     53/54: the key items of the question the answer never mentions
            (data/content/writing_topics.json: exam content, not in git; without it the check is skipped)

These are shallow checks: they catch nonsense and off-topic answers, they do not grade the content.
"""
import json
import re
from collections import Counter
from pathlib import Path

from writing.rules import issue, kiwi

ROOT = Path(__file__).resolve().parent.parent
TOPICS_FILE = ROOT / "data" / "content" / "writing_topics.json"
TOPICS = json.loads(TOPICS_FILE.read_text()) if TOPICS_FILE.exists() else {}


def check_nonsense(text):
    out = []
    jamo = re.findall(r"[ㄱ-ㅎㅏ-ㅣ]+", text)
    if jamo:
        out.append(issue("loose_jamo", "Loose consonants or vowels are not words.",
                         "พยัญชนะหรือสระที่แยกกันอยู่ไม่ใช่คำ", ", ".join(jamo[:3]), layer="content"))
    letters = re.sub(r"[\s\d.,?!'\"‘’“”:;()~∼\-–―…·%/]", "", text)
    if letters and len(re.findall(r"[가-힣]", letters)) / len(letters) < 0.8:
        out.append(issue("not_korean", "Most of the answer is not Korean.",
                         "คำตอบส่วนใหญ่ไม่ใช่ภาษาเกาหลี", layer="content"))
    sents = [re.sub(r"[\s.,?!]", "", s.text) for s in kiwi().split_into_sents(text)]
    repeated = [s for s, n in Counter(sents).items() if n > 1 and len(s) >= 5]
    if repeated:
        out.append(issue("repeated", "The same sentence is written more than once.",
                         "เขียนประโยคเดิมซ้ำมากกว่าหนึ่งครั้ง", repeated[0][:20], layer="content"))
    return out


def check_topic(rnd, number, text):
    groups = TOPICS.get(str(rnd), {}).get(str(number), [])
    if not groups:
        return []
    flat = re.sub(r"\s", "", text)
    missing = [g for g in groups if not any(w.replace(" ", "") in flat for w in g["any"])]
    if any(g.get("core") for g in missing) or len(missing) > len(groups) / 2:
        return [issue("off_topic", "Your answer does not seem to be about this question.",
                      "คำตอบดูเหมือนไม่ได้ตอบโจทย์ข้อนี้", layer="content")]
    return [issue("missing_item", f"Not mentioned: {g['en']}", f"ยังไม่ได้กล่าวถึง: {g['th']}", layer="content")
            for g in missing]
