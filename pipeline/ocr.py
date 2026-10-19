"""Step 1 of the pipeline: OCR every exam PDF page with Apple Vision.

Most official TOPIK PDFs are images, so we render each page to PNG and run
Apple's built-in OCR (via ocrmac). We save text AND position (bounding box)
for every line, because later steps use position to rebuild the layout
(e.g. which choice is ① ② ③ ④ when OCR misreads the circled number).

Output: data/ocr/<pdf name>/page_001.json  (one file per page)
Run:    .venv/bin/python pipeline/ocr.py            (skips pages already done)
"""
import json
import sys
import tempfile
import time
from pathlib import Path

import pymupdf
from ocrmac import ocrmac

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "ocr"
DPI = 200  # higher DPI = sharper image = better OCR, but slower


def ocr_page(page, png_path):
    page.get_pixmap(dpi=DPI).save(png_path)
    lines = ocrmac.OCR(str(png_path), language_preference=["ko-KR", "en-US"],
                       recognition_level="accurate").recognize()
    # bbox from Vision = (x, y, width, height), 0–1, origin bottom-left.
    # Convert to top-left origin so "y" grows downward like reading order.
    return [{"text": t, "conf": round(c, 2),
             "x": round(b[0], 4), "y": round(1 - b[1] - b[3], 4),
             "w": round(b[2], 4), "h": round(b[3], 4)} for t, c, b in lines]


def main(only=None):
    pdfs = sorted(RAW.glob("*.pdf"))
    if only:
        pdfs = [p for p in pdfs if only in p.name]
    with tempfile.TemporaryDirectory() as tmp:
        png = Path(tmp) / "page.png"
        for pdf in pdfs:
            out_dir = OUT / pdf.stem
            out_dir.mkdir(parents=True, exist_ok=True)
            doc = pymupdf.open(pdf)
            start = time.time()
            for i, page in enumerate(doc, 1):
                out = out_dir / f"page_{i:03d}.json"
                if out.exists():
                    continue
                out.write_text(json.dumps(ocr_page(page, png), ensure_ascii=False, indent=1))
            print(f"{doc.page_count:3} pages  {time.time() - start:5.1f}s  {pdf.name}", flush=True)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
