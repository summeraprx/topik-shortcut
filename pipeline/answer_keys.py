"""Step 2 of the pipeline: read the official answer keys (Listening + Reading).

Why a special script? Apple OCR reads circled answers (①②③④) badly on full pages.
Method:
  1. OCR the page -> find question numbers and the 정답 column -> locate every answer cell.
     Missing numbers are filled in with a straight-line fit (rows are evenly spaced).
  2. OCR each cell alone. Precise but misses some cells.
  3. Cells OCR did read become templates for ① ② ③ ④. Every cell is matched to the
     most similar template (correlation). OCR and template must agree, or the cell is flagged.

Output: data/processed/answer_keys.json and data/processed/answer_key_audit/*.png
        (audit sheets: every cell image next to its predicted answer, for human review)
Run:    .venv/bin/python pipeline/answer_keys.py
"""
import io
import itertools
import json
import re
from pathlib import Path

import numpy as np
import pymupdf
from ocrmac import ocrmac
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "processed"
AUDIT = OUT / "answer_key_audit"
DPI = 300
CIRCLED = {"①": 1, "②": 2, "③": 3, "④": 4, "1": 1, "2": 2, "3": 3, "4": 4}
MIN_SCORE = 0.85  # template match below this -> flag for human review


def render(page, dpi, clip=None):
    pm = page.get_pixmap(dpi=dpi, clip=clip, colorspace=pymupdf.csGRAY)
    return Image.open(io.BytesIO(pm.tobytes("png")))


def ocr(img):
    """Return [(text, x, y, w, h)] with top-left origin, 0–1 coordinates."""
    buf = io.BytesIO()
    img.save(buf, "PNG")
    tmp = OUT / "_tmp_ocr.png"
    tmp.write_bytes(buf.getvalue())
    res = ocrmac.OCR(str(tmp), language_preference=["ko-KR"], recognition_level="accurate").recognize()
    return [(t.strip(), b[0], 1 - b[1] - b[3], b[2], b[3]) for t, _, b in res]


def find_rows(lines, first_q, x_lo, x_hi):
    """Question-number column in one half of the table -> y centre for every question."""
    digits = [(int(t), x, y + h / 2) for t, x, y, w, h in lines
              if re.fullmatch(r"[0-9]{1,2}", t) and x_lo <= x < x_hi]
    if not digits:
        return None, None
    x_min = min(x for _, x, _ in digits)
    col = [(q, x, yc) for q, x, yc in digits if x < x_min + 0.03 and first_q <= q < first_q + 25]
    if len(col) < 5:
        return None, None
    q, xs, yc = np.array(col).T
    slope, icpt = np.polyfit(q, yc, 1)          # y = slope * q + icpt
    keep = np.abs(yc - (slope * q + icpt)) < slope / 2   # drop misread numbers
    slope, icpt = np.polyfit(q[keep], yc[keep], 1)
    rows = {int(n): slope * n + icpt for n in range(first_q, first_q + 25)}
    num_right = max(x + w for t, x, y, w, h in lines
                    if re.fullmatch(r"[0-9]{1,2}", t) and x_lo <= x < x_min + 0.03)
    return rows, num_right


def answer_span(lines, x_lo, x_hi, num_right):
    """Answer column = gap between the number column and the 배점 (score) column."""
    score_x = [x for t, x, y, w, h in lines
               if t in ("2", "3") and num_right + 0.15 < x < x_hi]
    right = float(np.median(score_x)) if len(score_x) >= 5 else num_right + 0.25
    return num_right + 0.01, right - 0.01


def runs(mask):
    """[(start, end)] of consecutive True values."""
    out, start = [], None
    for i, v in enumerate(list(mask) + [False]):
        if v and start is None:
            start = i
        elif not v and start is not None:
            out.append((start, i))
            start = None
    return out


def clean_cell(img):
    """Keep only the answer symbol: drop table lines, take the widest ink blob, add padding.

    A circled digit is about as wide as it is tall; line fragments are 1–3 px wide.
    Faint old prints are contrast-stretched so OCR and matching can see them.
    """
    a = 255 - np.asarray(img, dtype=float)
    ink = a > 50
    ink[ink.mean(axis=1) > 0.5, :] = False           # horizontal table lines
    cols = runs(ink.any(axis=0))
    if not cols:
        return img
    x0, x1 = max(cols, key=lambda r: r[1] - r[0])    # widest blob = the symbol
    rows = runs(ink[:, x0:x1].any(axis=1))
    y0, y1 = max(rows, key=lambda r: r[1] - r[0])
    sym = a[y0:y1, x0:x1]
    sym = np.clip(sym * (255 / max(sym.max(), 1)), 0, 255)   # contrast stretch
    pad = max(8, (y1 - y0) // 2)
    out = np.zeros((y1 - y0 + 2 * pad, x1 - x0 + 2 * pad))
    out[pad:pad + y1 - y0, pad:pad + x1 - x0] = sym
    return Image.fromarray((255 - out).astype(np.uint8))


def cell_vector(img):
    a = 255 - np.asarray(img, dtype=float)
    ys, xs = np.nonzero(a > 80)
    if len(ys) == 0:
        return None
    a = a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    a = np.asarray(Image.fromarray(a).resize((40, 40)), dtype=float)
    a = a[9:31, 9:31].ravel()   # inside of the circle only: the ring is the same for ①②③④
    return (a - a.mean()) / (a.std() + 1e-6)


def font_templates():
    """Backup templates: ① ② ③ ④ drawn with a macOS font (used when OCR reads none)."""
    font = ImageFont.truetype("/System/Library/Fonts/Supplemental/AppleMyungjo.ttf", 80)
    out = {}
    for d, ch in enumerate("①②③④", 1):
        img = Image.new("L", (120, 120), 255)
        ImageDraw.Draw(img).text((10, 10), ch, font=font, fill=0)
        out[d] = cell_vector(img)
    return out


def without_ring(img):
    """White out everything outside the inner circle, then enlarge: ② -> plain 2."""
    a = np.asarray(img, dtype=float).copy()
    h, w = a.shape
    ys, xs = np.nonzero(a < 200)
    if len(ys) == 0:
        return img
    cy, cx = (ys.min() + ys.max()) / 2, (xs.min() + xs.max()) / 2
    r = min(ys.max() - ys.min(), xs.max() - xs.min()) / 2
    yy, xx = np.mgrid[0:h, 0:w]
    a[(yy - cy) ** 2 + (xx - cx) ** 2 > (0.68 * r) ** 2] = 255
    big = Image.fromarray(a.astype(np.uint8)).resize((w * 3, h * 3), Image.LANCZOS)
    return big


def kmeans(X, k, restarts=20, iters=20, seed=0):
    """Plain k-means with k-means++ starts; keep the run with the smallest total distance."""
    rng = np.random.default_rng(seed)
    best = None
    for _ in range(restarts):
        centers = [X[rng.integers(len(X))]]
        for _ in range(k - 1):
            d = np.min([((X - c) ** 2).sum(1) for c in centers], axis=0)
            centers.append(X[rng.choice(len(X), p=d / d.sum())])
        centers = np.array(centers)
        for _ in range(iters):
            labels = np.argmin([((X - c) ** 2).sum(1) for c in centers], axis=0)
            centers = np.array([X[labels == j].mean(0) if (labels == j).any() else centers[j]
                                for j in range(k)])
        cost = sum(((X[labels == j] - centers[j]) ** 2).sum() for j in range(k))
        if best is None or cost < best["cost"]:
            best = {"cost": cost, "labels": labels, "centers": centers}
    return best


def name_groups(centers, group_of, ocr_label):
    """Give each cluster a digit. OCR votes win; remaining clusters use font templates."""
    names, src = {}, {}
    for g in range(len(centers)):
        votes = [ocr_label[q] for q, gg in group_of.items() if gg == g and q in ocr_label]
        if votes:
            d = max(set(votes), key=votes.count)
            if d not in names.values():
                names[g], src[d] = d, "ocr"
    free_groups = [g for g in range(len(centers)) if g not in names]
    free_digits = [d for d in (1, 2, 3, 4) if d not in names.values()]
    best_perm = max(itertools.permutations(free_digits),
                    key=lambda p: sum(centers[g] @ FONT_TEMPLATES[d] for g, d in zip(free_groups, p)))
    for g, d in zip(free_groups, best_perm):
        names[g], src[d] = d, "font"
    return names, src


def read_section(page):
    W, H = page.rect.width, page.rect.height
    lines = ocr(render(page, DPI))
    cells = {}
    for first_q, (x_lo, x_hi) in ((1, (0.0, 0.5)), (26, (0.5, 1.0))):
        rows, num_right = find_rows(lines, first_q, x_lo, x_hi)
        if rows is None:
            raise ValueError(f"could not find question numbers {first_q}–{first_q + 24}")
        left, right = answer_span(lines, x_lo, x_hi, num_right)
        pitch = (rows[first_q + 1] - rows[first_q])
        for q, yc in rows.items():
            clip = pymupdf.Rect(left * W, (yc - pitch * 0.45) * H, right * W, (yc + pitch * 0.45) * H)
            cells[q] = clean_cell(render(page, 400, clip))

    # OCR each cell alone: first as-is, then with the circle ring erased (plain digit is easier)
    ocr_label = {}
    for q, img in cells.items():
        for candidate in (img, without_ring(img)):
            txt = "".join(t for t, *_ in ocr(candidate))
            found = [CIRCLED[ch] for ch in txt if ch in CIRCLED]
            if len(set(found)) == 1:
                ocr_label[q] = found[0]
                break

    # 1) Cluster all cells into 4 groups WITHOUT labels (same font in one PDF -> tight groups)
    vecs = {q: cell_vector(img) for q, img in cells.items()}
    good = [q for q in cells if vecs[q] is not None]
    groups = kmeans(np.array([vecs[q] for q in good]), k=4)
    group_of = dict(zip(good, groups["labels"]))

    # 2) Name each group: OCR majority vote if any, else best one-to-one match with font templates
    names, seed_src = name_groups(groups["centers"], group_of, ocr_label)
    templates = {names[g]: groups["centers"][g] for g in range(4)}

    result = {}
    for q in sorted(cells):
        if vecs[q] is None:
            result[q] = {"answer": None, "score": 0.0, "flag": "empty cell"}
            continue
        scores = {d: float(vecs[q] @ t / len(t)) for d, t in templates.items()}
        best = max(scores, key=scores.get)
        flag = None
        if scores[best] < MIN_SCORE:
            flag = "low match score"
        elif q in ocr_label and ocr_label[q] != best:
            flag = f"OCR says {ocr_label[q]}, cluster says {best}"
        result[q] = {"answer": best, "score": round(scores[best], 3), "flag": flag}
    return result, cells, seed_src


def audit_sheet(name, result, cells):
    """One image: every cell + predicted answer, so a human can check 50 answers in seconds."""
    tile_w, tile_h = 150, 60
    sheet = Image.new("L", (tile_w * 5, tile_h * 10), 255)
    draw = ImageDraw.Draw(sheet)
    for i, q in enumerate(sorted(cells)):
        x, y = (i // 10) * tile_w, (i % 10) * tile_h
        sheet.paste(ImageOps.contain(cells[q], (60, tile_h - 6)), (x + 40, y + 3))
        r = result[q]
        draw.text((x + 4, y + 22), f"{q}", fill=0)
        draw.text((x + 105, y + 22), f"={r['answer']}" + (" !" if r["flag"] else ""), fill=0)
    sheet.save(AUDIT / f"{name}.png")


def section_of(lines_text, order):
    head = " ".join(lines_text)
    if "듣기" in head:
        return "listening"
    if re.search(r"읽기|위기|여기|읽 기", head):
        return "reading"
    return ["listening", "reading"][order]


def main():
    global FONT_TEMPLATES
    FONT_TEMPLATES = font_templates()
    AUDIT.mkdir(parents=True, exist_ok=True)
    keys, flags = {}, []
    files = sorted(p for p in RAW.glob("*.pdf") if re.search(r"정답", p.name))
    for pdf in files:
        rnd = int(re.search(r"(\d+)회", pdf.name).group(1))
        doc = pymupdf.open(pdf)
        answer_pages = []
        for page in doc:
            lines = ocr(render(page, 150))
            n_digits = sum(bool(re.fullmatch(r"[0-9]{1,2}", t)) for t, *_ in lines)
            if n_digits >= 30:  # answer tables have ~100 numbers; Writing pages have < 10
                answer_pages.append((page, [t for t, x, y, w, h in lines if y < 0.25]))
        for order, (page, top) in enumerate(answer_pages):
            section = section_of(top, order)
            try:
                result, cells, seed_src = read_section(page)
            except ValueError as e:
                flags.append({"round": rnd, "section": section, "q": None, "why": f"page failed: {e}"})
                print(f"round {rnd:3} {section:9}  FAILED: {e}")
                continue
            keys.setdefault(str(rnd), {})[section] = [result[q]["answer"] for q in range(1, 51)]
            audit_sheet(f"{rnd}_{section}", result, cells)
            bad = [(q, r["flag"], r["score"]) for q, r in result.items() if r["flag"]]
            flags += [{"round": rnd, "section": section, "q": q, "why": f, "score": s} for q, f, s in bad]
            font_seeded = [d for d, s in seed_src.items() if s == "font"]
            counts = [keys[str(rnd)][section].count(d) for d in (1, 2, 3, 4)]
            print(f"round {rnd:3} {section:9}  flagged: {len(bad):2}  font-seeded: {font_seeded or '-'}  ①②③④={counts}")
    (OUT / "_tmp_ocr.png").unlink(missing_ok=True)
    (OUT / "answer_keys.json").write_text(json.dumps(keys, indent=1, sort_keys=True))
    (OUT / "answer_key_flags.json").write_text(json.dumps(flags, ensure_ascii=False, indent=1))
    print(f"\n{len(keys)} rounds, {len(flags)} flagged cells -> data/processed/")


if __name__ == "__main__":
    main()
