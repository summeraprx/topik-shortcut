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

## Data

Exam PDFs are downloaded from the official TOPIK site (topik.go.kr) and are **not** included in this repository. Copyright belongs to 국립국제교육원 (NIIED) and the original authors of the passages.
