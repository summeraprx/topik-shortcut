"""Writing checker, layer 3: spelling and grammar errors from a local model (language only).

The model must answer in a fixed JSON shape (Ollama structured output):
  {"errors": [{"original": "...", "correction": "...", "reason_en": "...", "reason_th": "..."}]}
Safety checks, like the citation check in RAG:
  - "original" must appear word for word in the answer, otherwise the error is invented -> dropped
  - original == correction, or a difference only in spaces -> dropped (spacing is layer 2's job)
"""
import json
import re
import urllib.request

from rag.search import OLLAMA

MODEL = "gemma4:e2b-it-qat"

SCHEMA = {
    "type": "object",
    "properties": {"errors": {"type": "array", "items": {
        "type": "object",
        "properties": {"original": {"type": "string"}, "correction": {"type": "string"},
                       "reason_en": {"type": "string"}, "reason_th": {"type": "string"}},
        "required": ["original", "correction", "reason_en", "reason_th"]}}},
    "required": ["errors"],
}

PROMPT = """You are a Korean teacher checking a TOPIK II writing answer.
Find ONLY spelling mistakes (맞춤법) and grammar mistakes (wrong particle, wrong ending, wrong conjugation).
Do NOT comment on spacing, style, content, or structure. Do NOT rewrite good sentences.
For each mistake give: the exact wrong words copied from the answer ("original"), the corrected words,
and a very short reason in English and in Thai. If there are no mistakes, return an empty list.

ANSWER:
{answer}"""


def find_errors(answer, model=MODEL):
    body = {"model": model, "stream": False, "format": SCHEMA, "options": {"temperature": 0},
            "messages": [{"role": "user", "content": PROMPT.format(answer=answer)}]}
    req = urllib.request.Request(f"{OLLAMA}/api/chat", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=600) as r:
        raw = json.loads(json.loads(r.read())["message"]["content"])

    kept, dropped = [], []
    for e in raw.get("errors", []):
        original, correction = e["original"].strip(), e["correction"].strip()
        if not original or original not in answer:
            dropped.append({**e, "why": "not in the answer (invented)"})
        elif re.sub(r"\s+", "", original) == re.sub(r"\s+", "", correction):
            dropped.append({**e, "why": "same text or spacing only"})
        else:
            kept.append({"rule": "ai_language", "layer": "ai", "excerpt": original, "correction": correction,
                         "en": f"{original} → {correction}: {e['reason_en']}",
                         "th": f"{original} → {correction}: {e['reason_th']}"})
    return kept, dropped
