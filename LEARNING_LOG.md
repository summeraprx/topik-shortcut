# Learning Log

## 2026-10-19 — Evaluating the extraction pipeline

- **Strict vs normalized accuracy:** strict = extracted text exactly equals the gold text; normalized = equal after removing all whitespace. The gap between them shows how many errors are only formatting (space vs line break) and not real content errors.
- **CER (character error rate)** = edit distance ÷ number of gold characters. Edit distance (Levenshtein) = minimum insertions, deletions and substitutions, computed with dynamic programming, keeping only two rows of the table.
- **Why CER uses normalized text:** whitespace choices are formatting, already measured by strict vs normalized. Removing whitespace makes CER count only real recognition errors (e.g. `2` vs `²`).
- **Bug I fixed:** `stats["ALL"] = total` was indented inside the `for` loop, so it ran on every pass and added a key to the dictionary while looping over it → `RuntimeError: dictionary changed size during iteration`. Indentation decides what belongs to a loop; use 4 spaces consistently.

## 2026-10-20 — RAG ("Ask TOPIK")

- **Chunks** = what search finds and the model cites: one per exam question, one per grammar card, each with an id.
- **BM25** (keyword): scores documents by matching terms, weighted by rarity (IDF) and normalised by length. Korean terms = Kiwi morphemes (바람/NNB).
- **Embeddings** (bge-m3): meaning vectors; cosine similarity finds related text across languages (an English question finds Korean content).
- **RRF** (Reciprocal Rank Fusion): merge ranked lists with score = Σ 1/(60 + rank). Equal-weight hybrid was *worse* than vectors for grammar questions — keyword noise from shared morphemes. Measure before assuming hybrid helps.
- **Query router**: pasted Korean sentence → BM25; grammar questions / English / Thai → vectors. Plus exact grammar-name matching. 98.3% → 99.8% hit@5.
- **Metrics**: hit@k (correct result in top k), MRR (mean of 1/rank of first correct result).
- **Faithfulness**: the model must cite source ids; any cited id that was not retrieved is flagged. Found a bug this way: the model copied ids from an "Appears in" list it saw in a card → moved those ids to hidden metadata.
- **Small models ignore "answer in the same language"** in the system prompt → detect the language in code and put the instruction at the end of the user message.
- **Test-set flaws are real**: some "lookup" queries were question stems shared by many questions — impossible to answer, so I removed shared sentences from that test.

## 2026-10-20 — Writing checker

- **Rules from official sources** beat guessing: the TOPIK guides say exactly what loses points (-ㅂ/습니다 endings, title, copying…). The official "(288자)" marks showed that length = characters incl. spaces.
- **Error injection** = make a test set without labelling: take correct texts, insert one known error, check that the right rule fires. Also measure **false alarms** on the clean texts — a checker that flags correct writing teaches the wrong thing.
- Kiwi's spacing model flagged 11 "errors" in a correct official answer (compound nouns and numbers, where spacing is optional) → only report *clear* errors (after a particle/ending; before a dependent piece).
- **Structured output** (JSON schema in Ollama) makes model answers machine-checkable; the "original must appear in the answer" check is the writing version of the RAG citation check.
- Small models **find** errors better than they **fix** them (5/6 found, 3/5 fixes right) → show AI items as "possible error here", and **guard** them with the rules (a fix into -합니다 was dropped).
