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

### Writing checker (Q51–54)

Three layers: **official rules** from the TOPIK guides (length in 원고지 characters, no -ㅂ/습니다/-요 endings in 53–54, no title, no copying the question, one sentence for 51–52, matching formality…), **language** (clear spacing errors with Kiwi, spoken expressions), and **AI** (spelling/grammar with a local model, shown as *possible* errors). Feedback in English and Thai.

Evaluated by injecting known errors into the **official model answers** (rounds 102, 96, 91):

| Layer | Result |
|---|---|
| Length counter | matches the official counts exactly (300, 288; 279 vs 280) |
| Rules + language | **64 / 64** injected errors caught (12 types), **0 false alarms** on the 12 clean official answers |
| AI (gemma4:e2b) | typos found **5 / 6**, **0** errors invented on clean essays; corrections right only **3 / 5** → shown as "possible error here", and corrections that break TOPIK rules are dropped |

**Caveat:** the spacing rules were tuned on these same answers, so 64/64 is a development score.

## Run it locally

Needs Python 3 (`.venv`), Node.js, and [Ollama](https://ollama.com) with `bge-m3` and `gemma4:e2b-it-qat`.
Exam data is not in the repo: download the PDFs and run the pipeline first (see `pipeline/`).

```bash
.venv/bin/python -m pipeline.export_web                              # data for the website -> data/web/
.venv/bin/uvicorn api.main:app --host 127.0.0.1 --port 8000          # Ask TOPIK + Writing checker API
cd web && npm run dev                                                # website: http://127.0.0.1:3000/ko
```

**Phone mode** (test on a phone over Wi-Fi): stop the normal servers, then run `./scripts/phone_mode.sh`. It prints a link with a random secret key; without that key, both the website and the API answer 401 (safe on shared Wi-Fi). Ctrl+C stops everything.

Website: Next.js 16 (App Router, cache components), TypeScript, Tailwind; pages in Korean / English / Thai (`/ko`, `/en`, `/th`).

## Data

Exam PDFs are downloaded from the official TOPIK site (topik.go.kr) and are **not** included in this repository. Copyright belongs to 국립국제교육원 (NIIED) and the original authors of the passages.
