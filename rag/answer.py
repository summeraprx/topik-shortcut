"""Ask TOPIK: retrieve chunks, let a local model answer ONLY from them, check its citations.

Run:  .venv/bin/python -m rag.answer "-는 바람에는 언제 써요?"

Prompt rules for the model:
  - use only the sources given; if they do not contain the answer, say so
  - cite every claim with the source id in brackets: [96-reading-3], [grammar:-는 바람에]
  - answer in the same language as the question
After the answer we check every [citation]: it must be one of the retrieved ids, otherwise it is
flagged as invented. That check is cheap and catches the most common RAG failure.
"""
import json
import re
import sys
import time
import urllib.request

from rag.search import OLLAMA, Searcher

CHAT_MODEL = "gemma4:e2b-it-qat"
TOP_K = 5
MAX_CHARS = 1200          # per source: keeps the prompt small enough for a small local model
LINKED = 2               # exam questions added per retrieved grammar card ("Appears in" links)
LANGUAGE = {"th": "Thai (ภาษาไทย)", "ko": "Korean (한국어)", "en": "English"}

SYSTEM = """You are a TOPIK II study assistant.
Answer ONLY with information from the SOURCES. If the sources do not contain the answer, say you could not find it in past exams.
After each fact, cite the source id in square brackets, exactly as written, e.g. [96-reading-3] or [grammar:-는 바람에].
Answer in the same language as the question (Korean, English or Thai). Keep it short: at most 6 sentences."""

CITATION = re.compile(r"\[([^\[\]]+)\]")


def chat(messages, model=CHAT_MODEL):
    body = {"model": model, "messages": messages, "stream": False, "options": {"temperature": 0.2}}
    req = urllib.request.Request(f"{OLLAMA}/api/chat", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.loads(r.read())["message"]["content"]


def language(text):
    """Thai script -> th; mostly Hangul -> ko; otherwise en. Grammar names (Korean) inside an
    English or Thai question must not make it "Korean", so Thai wins and Hangul must be the majority."""
    if re.search(r"[\u0E00-\u0E7F]", text):
        return "th"
    hangul = len(re.findall(r"[가-힣]", text))
    latin = len(re.findall(r"[A-Za-z]", text))
    return "ko" if hangul > latin else "en"


def with_linked_questions(hits, searcher):
    """A grammar card lists where it appears; add those exam questions so the model can quote them."""
    by_id = {c["id"]: c for c in searcher.chunks}
    have = {h["id"] for h in hits}
    extra = []
    for h in hits[:2]:
        if h["kind"] != "grammar":
            continue
        ids = sorted(h["meta"]["appears_in"], key=lambda q: -int(q.split("-")[0]))   # newest round first
        for qid in [q for q in ids if q not in have][:LINKED]:
            extra.append({**by_id[qid], "linked_from": h["id"]})
            have.add(qid)
    return hits + extra


def ask(question, searcher=None, k=TOP_K, model=CHAT_MODEL, follow_links=True):
    searcher = searcher or Searcher()
    t0 = time.time()
    hits = searcher.search(question, k=k)
    if follow_links:
        hits = with_linked_questions(hits, searcher)
    lang = language(question)
    sources = "\n\n".join(f"[{h['id']}]\n{h['text'][:MAX_CHARS]}" for h in hits)
    answer = chat([{"role": "system", "content": SYSTEM},
                   {"role": "user", "content": f"SOURCES:\n{sources}\n\nQUESTION: {question}\n\n"
                                               f"Answer in {LANGUAGE[lang]}. Cite source ids in [brackets]."}], model)
    retrieved = {h["id"] for h in hits}
    # "[a, b, c]" counts as three citations
    cited = [c.strip() for group in CITATION.findall(answer) for c in re.split(r"[,;]", group) if c.strip()]
    return {
        "question": question,
        "language": lang,
        "answer": answer,
        "retrieved": [h["id"] for h in hits],
        "citations": cited,
        "invalid_citations": [c for c in cited if c not in retrieved],
        "seconds": round(time.time() - t0, 1),
    }


if __name__ == "__main__":
    r = ask(" ".join(sys.argv[1:]))
    print(r["answer"])
    print(f"\n— retrieved: {r['retrieved']}")
    print(f"— cited: {r['citations']}  invalid: {r['invalid_citations'] or 'none'}  ({r['seconds']}s)")
