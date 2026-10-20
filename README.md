# TOPIK Shortcut

Analysis of real past TOPIK II exams (vocabulary and grammar frequency, question types, writing structures) to help learners prepare faster.

> Work in progress. See [SPEC.md](SPEC.md) for scope and design decisions.

## Results so far

**Extraction accuracy:** On a hand-checked gold set (TOPIK II round 102, 131 fields), the OCR → structuring pipeline reaches **89.3% exact field accuracy**, **93.9% ignoring whitespace**, and a **0.72% character error rate**.

| Field | n | Exact | Ignoring whitespace | CER |
|---|---|---|---|---|
| Choices | 50 | 100.0% | 100.0% | 0.00% |
| Instruction | 19 | 94.7% | 94.7% | 0.84% |
| Question text | 54 | 81.5% | 90.7% | 1.21% |
| Shared passage | 8 | 62.5% | 75.0% | 0.40% |
| **All** | **131** | **89.3%** | **93.9%** | **0.72%** |

Measured with `eval/eval_extraction.py`.

### Ask TOPIK (RAG)

Questions in Korean, English or Thai are answered **only from past exams and our grammar cards**, with a citation for every fact (`[96-reading-3]`, `[grammar:-는 바람에]`). Runs fully on a laptop: bge-m3 embeddings + `gemma4:e2b` via Ollama.

**Retrieval** — 1,070 test queries generated from our own data (KO/EN/TH), hit@5 / MRR:

| Search | grammar meaning | usage in exams* | difference | paraphrase | pasted exam sentence | **all** |
|---|---|---|---|---|---|---|
| keyword (BM25 on Kiwi morphemes) | 89.1% | 78.6% | 78.8% | 49.5% | **100%** | 78.6% / 0.76 |
| meaning (bge-m3 vectors) | 99.3% | 95.2% | 100% | 100% | 98.3% | 98.3% / 0.97 |
| hybrid (RRF, equal weight) | 98.0% | 86.7% | 91.5% | 100% | 100% | 94.5% / 0.92 |
| **router + grammar-name match** | **100%** | **100%** | **100%** | **100%** | 98.3% | **99.8% / 0.99** |

\* usage = top 5 + exam questions linked from the retrieved grammar card.

Findings: plain hybrid search was *worse* than vector search for grammar questions (shared morphemes add noise), but keyword search wins for pasted exam sentences — so a simple query router picks the right search per query.
**Caveat:** test queries are generated from templates and contain exact grammar names, so these numbers are optimistic; real user questions are harder.

**Answers** (12 real answers, local model): 21 citations, **0 invalid**; 11/12 in the question's language; 1 honest "not found"; median 16 s on an 8 GB MacBook.

## Data

Exam PDFs are downloaded from the official TOPIK site (topik.go.kr) and are **not** included in this repository. Copyright belongs to 국립국제교육원 (NIIED) and the original authors of the passages.
