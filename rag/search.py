"""Hybrid search: keyword (BM25 on Kiwi morphemes) + meaning (bge-m3 embeddings), merged with RRF.

Why both?
  - Keyword search finds exact grammar: "-는 바람에" -> 는/ETM 바람/NNB 에/JKB, matched morpheme by morpheme.
  - Meaning search finds content across languages: an English or Thai question still finds Korean chunks.
  - Reciprocal Rank Fusion (RRF) merges the two ranked lists without tuning weights:
        score(chunk) = sum over lists of 1 / (60 + rank in that list)

Build the index:  .venv/bin/python -m rag.search build
Try a query:      .venv/bin/python -m rag.search "-는 바람에가 나온 문제"
"""
import json
import math
import re
import sys
import urllib.request
from collections import Counter
from pathlib import Path

import numpy as np
from kiwipiepy import Kiwi

from rag.chunks import build as build_chunks

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "data" / "rag"
OLLAMA = "http://localhost:11434"
EMBED_MODEL = "bge-m3"
RRF_K = 60
BM25_WEIGHT = 1.0      # set from the evaluation (eval/eval_rag.py)
BM25_K1, BM25_B = 1.5, 0.75
SKIP_TAGS = ("SF", "SP", "SS", "SE", "SO", "SW", "SB")     # punctuation and symbols
ALLOMORPH = {"ᆯ": "을", "ᆫ": "은", "ᆷ": "음"}               # same ending, different spelling

_kiwi = None


def tokens(text):
    """Text -> search terms. Korean: morpheme/tag (바람/NNB). Latin words: lowercase."""
    global _kiwi
    _kiwi = _kiwi or Kiwi()
    out = []
    for t in _kiwi.tokenize(text):
        tag = t.tag.split("-")[0]
        if tag.startswith(SKIP_TAGS):
            continue
        if tag == "SL":
            out.append(t.form.lower())
        else:
            out.append(f"{ALLOMORPH.get(t.form, t.form)}/{tag}")
    return out


def embed(texts):
    """Ask Ollama for bge-m3 embeddings, normalised so a dot product = cosine similarity."""
    req = urllib.request.Request(f"{OLLAMA}/api/embed", method="POST",
                                 data=json.dumps({"model": EMBED_MODEL, "input": texts}).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        vecs = np.array(json.loads(r.read())["embeddings"], dtype=np.float32)
    return vecs / np.linalg.norm(vecs, axis=1, keepdims=True)


def build_index(batch=16):
    INDEX.mkdir(parents=True, exist_ok=True)
    chunks = build_chunks()
    docs = [tokens(c["text"]) for c in chunks]
    vectors = np.vstack([embed([c["text"] for c in chunks[i:i + batch]]) for i in range(0, len(chunks), batch)])
    (INDEX / "chunks.json").write_text(json.dumps(chunks, ensure_ascii=False))
    (INDEX / "tokens.json").write_text(json.dumps(docs, ensure_ascii=False))
    np.save(INDEX / "vectors.npy", vectors)
    print(f"{len(chunks)} chunks, {vectors.shape[1]}-dim vectors -> {INDEX}")


def route(query):
    """Pick the search that works best for this kind of query (decided by eval/eval_rag.py):
    a pasted Korean sentence -> keyword search (BM25); a question about grammar, or any
    English/Thai query -> meaning (vector) search."""
    import re
    korean_only = re.fullmatch(r"[가-힣0-9\s.,()'\"~·%]+", query.strip()) is not None
    asks_grammar = re.search(r"(^|\s)-", query) or query.strip().endswith("?")
    return ("bm25", 1.0) if korean_only and not asks_grammar and len(query.strip()) >= 8 else ("vector", 1.0)


class Searcher:
    def __init__(self):
        self.chunks = json.loads((INDEX / "chunks.json").read_text())
        self.vectors = np.load(INDEX / "vectors.npy")
        docs = json.loads((INDEX / "tokens.json").read_text())
        self.tf = [Counter(d) for d in docs]
        self.lengths = np.array([len(d) for d in docs])
        self.avg_len = self.lengths.mean()
        df = Counter(term for d in docs for term in set(d))
        n = len(docs)
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}
        # grammar names for exact matching: "-는 김에" -> "-는김에" (spaces removed)
        self.names = []
        for i, c in enumerate(self.chunks):
            if c["kind"] == "grammar":
                for alt in c["meta"]["name"].split(" / "):
                    key = re.sub(r"\s+", "", alt)
                    if key.startswith("-") and len(key) >= 2:
                        self.names.append((key, i))
        self.names.sort(key=lambda x: -len(x[0]))        # longest first: -(으)ㄹ 수도 있다 before -(으)ㄹ 수

    def named_cards(self, query):
        """Grammar cards whose exact name ("-는 김에") is written in the query, longest names first."""
        q = re.sub(r"\s+", "", query)
        found = []
        for key, i in self.names:
            if key in q and i not in found:
                found.append(i)
                q = q.replace(key, " ")         # so "-(으)ㄹ 수" does not match again inside a longer name
        return found

    def bm25(self, query):
        terms = tokens(query)
        scores = np.zeros(len(self.chunks))
        for i, tf in enumerate(self.tf):
            norm = BM25_K1 * (1 - BM25_B + BM25_B * self.lengths[i] / self.avg_len)
            scores[i] = sum(self.idf.get(t, 0) * tf[t] * (BM25_K1 + 1) / (tf[t] + norm) for t in terms if t in tf)
        return scores

    def vector(self, query, qvec=None):
        return self.vectors @ (qvec if qvec is not None else embed([query])[0])

    def search(self, query, k=6, mode="auto", qvec=None, bm25_weight=BM25_WEIGHT, use_names=True):
        """mode: 'auto' (router), 'bm25', 'vector' or 'hybrid'. Returns the top k chunks.
        bm25_weight: how much the keyword list counts in the fusion (vector list counts 1)."""
        if mode == "auto":
            mode, bm25_weight = route(query)
        ranked = {}
        if mode in ("bm25", "hybrid"):
            s = self.bm25(query)
            ranked["bm25"] = [i for i in np.argsort(-s) if s[i] > 0]
        if mode in ("vector", "hybrid"):
            ranked["vector"] = list(np.argsort(-self.vector(query, qvec)))
        fused = Counter()
        for rank, i in enumerate(self.named_cards(query) if use_names else [], 1):
            fused[i] += 1.0 - rank * 0.01           # exact grammar name in the query: put that card first
        for name, order in ranked.items():
            weight = bm25_weight if (name == "bm25" and mode == "hybrid") else 1.0
            for rank, i in enumerate(order[:50], 1):
                fused[i] += weight / (RRF_K + rank)
        return [{**self.chunks[i], "score": round(score, 4)} for i, score in fused.most_common(k)]


if __name__ == "__main__":
    if sys.argv[1:] == ["build"]:
        build_index()
    else:
        for hit in Searcher().search(" ".join(sys.argv[1:])):
            print(f"{hit['score']:.4f}  {hit['id']:28}  {hit['text'][:60]!r}")
