# TOPIK Shortcut — Project Spec (v1)

> Status: DRAFT — waiting for owner approval. No code runs before approval.
> Last updated: 2026-10-19

## 1. Goal

A phone-friendly website that helps people pass **TOPIK II (PBT)** faster by analyzing
**real past exams**: vocabulary and grammar frequency, question types, writing answer
structures, and tips.

- **Now:** portfolio project for AI engineer job applications (Korean companies).
  Only user = the developer.
- **Later:** public launch, Thai market first, English for worldwide users.

Skills this project must prove: **LLM pipeline, prompt engineering, RAG, evaluation, Claude Code workflow.**

## 2. Scope

| v1 (3 days) | v2 (later) |
|---|---|
| Start with 2–3 exam rounds (all 12 public rounds already downloaded) | Process all 12 rounds |
| Reading + Writing | Listening (transcripts) |
| Vocabulary + grammar frequency (all items, not only top) | Full grammar coverage |
| Question type ↔ question number map, with real exam instruction words explained | Grammar exercises (interactive) |
| Writing: sentence-by-sentence structure analysis + templates for Q51–54 | Spaced repetition (SRS) |
| Writing checker: rules + local LLM (spacing, spelling, writing rules) | Switch checker to Claude API |
| RAG "Ask TOPIK" with citations (round + question number) | Login (email, min age 14), profile, privacy policy |
| Answer-choice distribution (shown as a tip only) | Kakao login, mobile app |
| Interface: Korean / English / Thai | TOPIK I, IBT |
| Evaluation for extraction, RAG, checker | Upcoming exam schedule |

Not in scope: mock tests, other people's tips (owner writes all tips), user accounts.

## 3. Key decisions and reasons

| Decision | Reason |
|---|---|
| **Python** for all data + AI code | Main language for AI jobs; owner knows basic Python |
| **Next.js** for website | Owner's choice; phone layout, 3 languages, can become app (PWA) later |
| **FastAPI** (Python) for AI endpoints | Keeps all AI code in Python; Next.js only calls it |
| **Supabase** (Postgres + pgvector) | Free tier, SQL is good for statistics, vector search for RAG, auth ready for v2 |
| **Kiwi** (kiwipiepy) for Korean analysis | Accurate, easy install on Mac (no Java), fast, maintained. Replaceable module |
| **Own grammar rules on top of Kiwi** | Kiwi splits morphemes but does not detect patterns like ~는 바람에 |
| **Ollama, small models** (8GB Mac) | Free, private. Weak Korean → measured in evaluation |
| **bge-m3** embeddings via Ollama | Multilingual (KR/EN/TH), runs on 8GB |
| **PDF reading by Claude Code, checked by owner** | Vision models do not fit 8GB RAM; pipeline LLM step stays swappable |
| **Translations stored in DB, made once** | No translation API at runtime = free and safe |
| **Online only** | Simpler; offline cache in v2 |
| **Round 35+ only** | Current TOPIK II format since 2014; older format breaks statistics |
| **Store instruction wording per round** | 2021 revision changed question instructions (발문); show old + new wording |
| **Rule checks before LLM in Writing checker** | Character count, -다 ending, no spoken style are exact rules; LLM only for what rules cannot do |

## 4. Architecture

```
[PDFs on Mac only] → pipeline/extract → data/processed (JSON, validated by Pydantic)
                   → pipeline/analyze (Kiwi + grammar rules → frequency stats)
                   → pipeline/embed (bge-m3)  → Supabase (tables + pgvector)

Next.js website ──read──▶ Supabase (analysis data, public read-only)
       └──────────call──▶ FastAPI (localhost) ──▶ Ollama (LLM + embeddings)
                                               └─▶ Supabase (vector search)
```

**Important limit:** Ollama runs only on the owner's Mac. So in v1 the **deployed website shows
analysis pages only**; "Ask TOPIK" and the Writing checker run **locally** and are shown in the
demo video. They go live in v2 with the Claude API behind a server function.

## 5. Data model (draft)

- `exams` — round, year, section
- `questions` — round, section, number, question_type, instruction, passage, choices (json), answer, image_path
- `lemmas` — lemma, part_of_speech, count, translations (en, th), context_note
- `grammar_patterns` — pattern (e.g. ~는 바람에), meaning, translations, count
- `occurrences` — links lemmas/patterns ↔ questions (sentence + position)
- `question_types` — type, question numbers, instruction keywords + meanings (e.g. 그림 = picture)
- `writing_templates` — question (51–54), task type (graph, table, opinion…), structure steps, model answer
- `tips` — section, question numbers, text (KR/EN/TH), written by owner
- `chunks` — text, source (round, question), embedding vector(1024)

## 6. Evaluation plan

| What | How | Metric |
|---|---|---|
| Extraction | Owner hand-checks 1 round = gold set | Field accuracy (%) |
| Kiwi + grammar rules | 50 hand-labeled sentences | Precision / recall |
| RAG | ~15–20 test questions with known source | Hit rate @5, answer has correct citation |
| Writing checker | ~10 sample answers with known errors | Errors found / false alarms; local model vs rules |

Owner writes the evaluation scripts (with guidance).

## 7. 3-day plan

| Day | Build |
|---|---|
| 1 | Setup (Python env, Git, Supabase, Ollama). Pydantic schema. Extract 2–3 rounds, owner checks. Kiwi + grammar rules. Load to Supabase. |
| 2 | Embeddings + RAG "Ask TOPIK" (FastAPI). Writing checker. Translations (EN/TH) of word/grammar lists. All evaluations. |
| 3 | Next.js website (KR/EN/TH, phone layout), deploy analysis pages. README (KR + EN), architecture diagram, eval numbers. |

Demo video: later (after v1).

Risk: Day 1 PDF extraction and Day 3 Next.js are the tightest. Fallback: cut to 2 rounds, fewer pages.

## 8. Working rules

- Claude Code **asks permission before every action** (files, commands, web, connectors).
- Claude Code writes code → owner reads, runs, and changes something small in each part.
- Owner keeps `LEARNING_LOG.md` (becomes interview notes).
- Owner: TOPIK 4, IELTS 6.5 → Korean README written by Claude, reviewed by owner; explanations in simple English.

## 9. Safety and legal

- No secret keys in website code or Git. `.env` in `.gitignore`. Supabase Row Level Security: public read-only.
- PDFs and extracted exam text stay on Mac / Supabase, **never in Git**.
- Download PDFs only from official topik.go.kr.
- Repo private now; later split: public code + sample data, private content (exam text, tips).
- Show only short exam excerpts with source (e.g. "Source: 제83회 TOPIK II, 국립국제교육원").
- Ask NIIED (국립국제교육원) for permission **before** any paid version.
- Some passages have **other original authors** who need separate permission (stated on topik.go.kr).
- No personal data collected in v1.

## 10. Data source (downloaded 2026-10-19)

From official topik.go.kr board (TWSTDY0100), saved in `data/raw/` (never in Git):
- 12 TOPIK II rounds: 35, 36, 37, 41, 47, 52, 60, 64, 83, 91, 96, 102
- Each: Reading, Listening + Writing booklet, Listening transcript (듣기 통합), answer key
- Rounds 36, 37: one combined booklet. Older rounds are B형 / 홀수형 forms
- Rounds 52, 60: answer key includes Writing scoring criteria (채점기준표)
- Guides: 평가틀 안내, 발문 안내 (2021), 쓰기 답안 작성 방법 (2017), 원고지 사용법
- Not downloaded: audio files (v2), TOPIK I

## 11. Pipeline status (2026-10-19)

| Step | Script | Status |
|---|---|---|
| OCR all PDFs (Apple Vision) | `pipeline/ocr.py` | ✅ 910 pages, 24,122 lines, 3% low-confidence (< 0.5). 34 near-empty pages = 33 intentional blank pages + 1 picture-only page (round 37 p.3) |
| Answer keys | `pipeline/answer_keys.py` | ✅ Rounds 102, 96, 91: checked by owner via audit sheets, correct. Also 0 flags: 83, 60, 64 Listening |
| | | ⏸ Later, "0 flags but not proven" (some digits named from font templates): 52, 47 Reading |
| | | ⏸ Later, not reliable: 35, 36 Listening, 37, 47 Listening, 64 Reading |
| | | ⏸ Later, page failed (question numbers not found): 36 Reading, 41 Listening, 41 Reading. Fix by: Claude reads image / owner types / improve script |
| Ask TOPIK (RAG) | `rag/`, `eval/eval_rag.py` | ✅ Local: 260 chunks (162 questions + 98 grammar cards), bge-m3 + gemma4:e2b via Ollama. Router + name match: 99.8% hit@5 on 1,070 generated queries; answers: 0 invalid citations / 21. Index is a local file (`data/rag/`); Supabase pgvector later |
| Writing checker | `writing/`, `eval/eval_writing.py` | ✅ Q51–54, 3 layers (rules / language / AI), EN+TH feedback. Rules+language 64/64 injected errors, 0 false alarms on official answers; AI typos 5/6, fixes 3/5 |
| Structure questions | `pipeline/structure.py` | ✅ Rounds 102, 96, 91: 150/150 Reading + 12/12 Writing found. Human fixes in `data/corrections/` |
| Gold set + evaluation | `pipeline/review_page.py`, `eval/eval_extraction.py` | ✅ Round 102 reviewed by owner (131 fields). Before fixes: 89.3% exact, CER 0.72%. After fixes: 95.4% exact, CER 0.62% (development set, so optimistic) |

Known data facts:
- **Passages withheld for copyright** in the official PDFs ("저작권 관련 법령에 따라 본 문항의 지문은 공개하지 않습니다"): Q42–43 in rounds 102, 96, 91; Q23–24 in round 102. Flagged as `passage_withheld`; analysis skips the notice text.
- Remaining errors on the gold set are real OCR misreads (`²`, `《`, a missing `.`) and charts/images (Q10 graph, Q53 chart, Q51 email screenshot).

Answer key method: locate cells by position → OCR each cell (also with circle ring erased) →
k-means clusters of symbol shapes → name clusters by OCR votes → flag disagreements / low similarity →
audit sheet image for human check.

## 12. Open items

- **Before public launch:** owner reviews ALL content (grammar in `content/grammar/` and vocabulary), including the 8 grammar points looked at on 2026-10-20. Until then it is Claude-written and labelled as not yet reviewed. Priority: Thai wording and Rules.
- Later (if time): round 96 as held-out **test set** for an honest accuracy number
- Later (if time): `eval_extraction.py` option to evaluate the current pipeline output (not the review-time snapshot)
- Later: describe Q53 / Q10 charts from page images
- Grammar patterns: auto-mined from data + labeled by Claude → owner reviews list
- Owner's tips and Writing core ideas (owner provides)
- Ollama chat model choice (test 2 small models on Day 2)
