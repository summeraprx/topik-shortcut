# Learning Log

## 2026-10-19 — Evaluating the extraction pipeline

- **Strict vs normalized accuracy:** strict = extracted text exactly equals the gold text; normalized = equal after removing all whitespace. The gap between them shows how many errors are only formatting (space vs line break) and not real content errors.
- **CER (character error rate)** = edit distance ÷ number of gold characters. Edit distance (Levenshtein) = minimum insertions, deletions and substitutions, computed with dynamic programming, keeping only two rows of the table.
- **Why CER uses normalized text:** whitespace choices are formatting, already measured by strict vs normalized. Removing whitespace makes CER count only real recognition errors (e.g. `2` vs `²`).
- **Bug I fixed:** `stats["ALL"] = total` was indented inside the `for` loop, so it ran on every pass and added a key to the dictionary while looping over it → `RuntimeError: dictionary changed size during iteration`. Indentation decides what belongs to a loop; use 4 spaces consistently.
