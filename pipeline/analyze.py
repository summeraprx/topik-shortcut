"""Step 4 of the pipeline: frequency analysis with Kiwi.

Input:  data/processed/questions_<round>.json, data/processed/answer_keys.json
Output: data/processed/analysis/
          vocab.json                every content word (dictionary form) with counts and examples
          grammar_candidates.json   auto-mined grammar patterns (to be labelled, then reviewed)
          question_types.json       instruction -> question numbers per round
          answer_distribution.json  how often ① ② ③ ④ is the answer
Run:    .venv/bin/python pipeline/analyze.py 102 96 91

How words are counted:
  - Kiwi splits text into morphemes:  예상/NNG 하/XSV ᆫ/ETM 대로/NNB
  - Content words become dictionary forms: 먹/VV -> 먹다, 예상/NNG + 하/XSV -> 예상하다
  - A shared passage is counted once per group, not once per question.
  - Passages withheld for copyright (notice text only) are skipped.
How grammar is mined:
  - Start at an ending (-는, -기, -어 …) and extend through grammar-only pieces
    (dependent nouns like 바람/셈/리, particles, auxiliary verbs, 이다 …) up to 4 pieces.
  - Keep sequences seen at least MIN_COUNT times. A Claude labelling step names them;
    the owner reviews the list.
"""
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

from kiwipiepy import Kiwi

ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "data" / "processed"
OUT = PROCESSED / "analysis"

CONTENT = {"NNG", "NNP", "VV", "VA", "MAG", "XR"}        # words learners study
VERB_SUFFIX = {"XSV", "XSA"}                               # 예상+하다, 따뜻+하다
GRAMMAR_START = {"ETM", "ETN", "EC"}                       # patterns start at an ending
GRAMMAR_PIECE = ("J", "E", "NNB", "VX", "VCP", "VCN", "XSV", "XSA")
GRAMMAR_NOUNS = {"덕분", "때문", "탓", "대신", "바람", "반면", "가능성"}      # grammar nouns Kiwi tags NNG
GRAMMAR_VERBS = {"있", "없", "하", "되", "않", "말", "보", "알", "모르"}       # verbs inside patterns (수 있다, -야 하다)
TRAILING = ("EP", "EF", "EC", "ETM", "JKS", "JKO", "JX", "JKG")              # pieces that belong to what comes next
ALLOMORPH = {"ᆯ": "(으)ㄹ", "을": "(으)ㄹ", "ᆫ": "(으)ㄴ", "은": "(으)ㄴ", "ᆷ": "(으)ㅁ", "음": "(으)ㅁ"}
BOILERPLATE_MIN = 3     # a sentence repeated in this many questions is a question stem, not content
BOILERPLATE_LEN = 8     # ...but only real sentences: short repeated choices like "은행" are vocabulary
EU_ENDINGS = {"면", "니까", "니", "러", "려고", "려면", "며", "면서", "므로", "ㄴ데", "세요", "십시오"}  # take (으)
TOO_BASIC = {"어", "고", "게", "지", "다"}   # single endings too basic to be a "shortcut" on their own
MAX_LEN = 4
MIN_COUNT = 2
EXAMPLES = 3

kiwi = Kiwi()


def base_tag(tag):
    return tag.split("-")[0]           # VV-I (irregular) -> VV


def units(questions):
    """Text pieces to analyse, with where they come from. Shared passages only once per group."""
    seen_passages = set()
    for q in questions:
        qid = f"{q['round']}-{q['section']}-{q['number']}"
        if q["shared_passage"] and not q["passage_withheld"]:
            key = (q["round"], q["section"], q["shared_passage"])
            if key not in seen_passages:
                seen_passages.add(key)
                yield qid, "passage", q["shared_passage"]
        if q["text"] and not (q["passage_withheld"] and "공개하지 않습니다" in q["text"]):
            yield qid, "question", q["text"]
        for i, choice in enumerate(q["choices"], 1):
            yield qid, "answer_choice" if i == q["answer"] else "choice", choice


def boilerplate_sentences(questions):
    """Sentences repeated across many questions = question stems (e.g. '알맞은 것을 고르십시오')."""
    where = defaultdict(set)
    for qid, _, text in units(questions):
        for sent in kiwi.split_into_sents(text):
            where[" ".join(sent.text.split())].add(qid)
    return {s: len(q) for s, q in where.items() if len(q) >= BOILERPLATE_MIN and len(s) >= BOILERPLATE_LEN}


def lemmas(tokens):
    """Content words in dictionary form. Noun/root + 하다/되다 suffix becomes one verb."""
    out, i = [], 0
    while i < len(tokens):
        t, tag = tokens[i], base_tag(tokens[i].tag)
        nxt = tokens[i + 1] if i + 1 < len(tokens) else None
        if tag in ("NNG", "XR") and nxt and base_tag(nxt.tag) in VERB_SUFFIX:
            out.append((t.form + nxt.form + "다", "VV" if base_tag(nxt.tag) == "XSV" else "VA"))
            i += 2
            continue
        if tag in ("VV", "VA"):
            out.append((t.form + "다", tag))
        elif tag in CONTENT:
            out.append((t.form, tag))
        i += 1
    return out


def is_grammar_piece(token):
    tag = base_tag(token.tag)
    return (tag.startswith(GRAMMAR_PIECE) or (tag == "NNG" and token.form in GRAMMAR_NOUNS)
            or (tag in ("VV", "VA") and token.form in GRAMMAR_VERBS))


def grammar_sequences(tokens):
    """Sequences that start at an ending and continue through grammar pieces (1..MAX_LEN).
    Trailing tense/sentence-final pieces are cut: 고 있 다 -> 고 있, 수 있 는 -> 수 있.
    A single piece is kept only for connective endings (-어서, -니까, -도록)."""
    found = set()
    for i, t in enumerate(tokens):
        if base_tag(t.tag) not in GRAMMAR_START:
            continue
        seq = [t]
        for nxt in tokens[i + 1:i + MAX_LEN]:
            if not is_grammar_piece(nxt):
                break
            seq.append(nxt)
        for end in range(len(seq), 0, -1):
            cut = seq[:end]
            while len(cut) > 1 and base_tag(cut[-1].tag).startswith(TRAILING):
                cut = cut[:-1]
            if len(cut) == 1 and (base_tag(cut[0].tag) != "EC" or cut[0].form in TOO_BASIC):
                continue
            key = (i, len(cut))
            if key not in found:
                found.add(key)
                yield cut, tokens


def pattern_key(seq):
    """ᆯ/을 -> (으)ㄹ, ᆫ/은 -> (으)ㄴ so sound variants of one grammar point are counted together."""
    parts = []
    for t in seq:
        tag = base_tag(t.tag)
        form = t.form
        if tag in ("ETM", "ETN"):
            form = ALLOMORPH.get(form, form)
        elif tag.startswith("E") and (form.startswith("으") or form in EU_ENDINGS):
            form = "(으)" + form.removeprefix("으")          # 으면 / 면 -> (으)면
        parts.append(f"{form}/{tag}")
    return " ".join(parts)


def add_example(entry, sentence, qid):
    if len(entry["examples"]) < EXAMPLES and all(e["sentence"] != sentence for e in entry["examples"]):
        entry["examples"].append({"sentence": sentence, "source": qid})


def analyse(questions):
    stems = boilerplate_sentences(questions)
    vocab = defaultdict(lambda: {"count": 0, "rounds": set(), "questions": set(), "pos": set(),
                                 "where": defaultdict(int), "examples": []})
    grammar = defaultdict(lambda: {"count": 0, "rounds": set(), "questions": set(), "examples": []})
    total_tokens = 0

    for qid, where, text in units(questions):
        rnd = int(qid.split("-")[0])
        for sent in kiwi.split_into_sents(text, return_tokens=True):
            sentence = " ".join(sent.text.split())
            if sentence in stems:
                continue
            tokens = [t for t in sent.tokens if base_tag(t.tag) not in ("SF", "SP", "SS", "SE", "SO", "SW")]
            total_tokens += len(tokens)
            for lemma, tag in lemmas(tokens):
                if tag == "NNP":          # names (mostly fictional: 김민수, 인주시)
                    continue
                v = vocab[lemma]
                v["pos"].add(tag)
                v["count"] += 1
                v["rounds"].add(rnd)
                v["questions"].add(qid)
                v["where"][where] += 1
                add_example(v, sentence, qid)
            for seq, _ in grammar_sequences(tokens):
                g = grammar[pattern_key(seq)]
                g["count"] += 1
                g["rounds"].add(rnd)
                g["questions"].add(qid)
                add_example(g, sentence, qid)
    return vocab, grammar, total_tokens, stems


def drop_subsumed(grammar):
    """'는/ETM 바람/NNB' is redundant when '는/ETM 바람/NNB 에/JKB' covers (almost) all its uses."""
    keep = {}
    for key, g in grammar.items():
        longer = [o for k, o in grammar.items() if k.startswith(key + " ")]
        if not any(o["count"] >= 0.8 * g["count"] for o in longer):
            keep[key] = g
    return keep


def question_types(questions):
    types = defaultdict(lambda: defaultdict(list))
    for q in questions:
        if not q["instruction"]:
            continue
        # "※ [9~12] 다음 글 ... (각 2점)" -> "다음 글 ..."  (same type across rounds)
        name = re.sub(r"^※\s*\[[^\]]*\]\s*|\(각\s*\d+\s*점\)\s*$", "", q["instruction"]).strip()
        types[f"{q['section']}: {name}"][q["round"]].append(q["number"])
    return {name: {str(r): nums for r, nums in sorted(rounds.items())} for name, rounds in types.items()}


def answer_distribution(rounds):
    keys = json.loads((PROCESSED / "answer_keys.json").read_text())
    out = {}
    for rnd in rounds:
        for section, answers in keys.get(str(rnd), {}).items():
            out.setdefault(str(rnd), {})[section] = {str(d): answers.count(d) for d in (1, 2, 3, 4)}
    return out


def to_json(table, kind):
    rows = []
    for key, v in table.items():
        row = {"count": v["count"], "rounds": sorted(v["rounds"]), "n_questions": len(v["questions"]),
               "examples": v["examples"]}
        if kind == "vocab":
            row = {"lemma": key, "pos": sorted(v["pos"]), **row, "where": dict(v["where"])}
        else:
            row = {"pattern": key, **row}
        rows.append(row)
    return sorted(rows, key=lambda r: (-len(r["rounds"]), -r["count"]))


def main(rounds):
    questions = []
    for rnd in rounds:
        questions += json.loads((PROCESSED / f"questions_{rnd}.json").read_text())

    vocab, grammar, total_tokens, stems = analyse(questions)
    grammar = {k: g for k, g in grammar.items() if g["count"] >= MIN_COUNT}
    grammar = drop_subsumed(grammar)

    OUT.mkdir(parents=True, exist_ok=True)
    files = {
        "vocab.json": to_json(vocab, "vocab"),
        "grammar_candidates.json": to_json(grammar, "grammar"),
        "question_types.json": question_types(questions),
        "answer_distribution.json": answer_distribution(rounds),
        "question_stems.json": dict(sorted(stems.items(), key=lambda kv: -kv[1])),
    }
    for name, data in files.items():
        (OUT / name).write_text(json.dumps(data, ensure_ascii=False, indent=1))

    v, g = files["vocab.json"], files["grammar_candidates.json"]
    print(f"rounds {rounds}: {len(questions)} questions, {total_tokens} tokens")
    print(f"vocab: {len(v)} distinct words, {sum(r['count'] for r in v)} occurrences, "
          f"{sum(len(r['rounds']) == len(rounds) for r in v)} in every round")
    print(f"grammar candidates: {len(g)}, {sum(len(r['rounds']) == len(rounds) for r in g)} in every round")
    print(f"question types: {len(files['question_types.json'])}, question stems excluded: {len(stems)}")


if __name__ == "__main__":
    main([int(r) for r in sys.argv[1:]] or [102, 96, 91])
