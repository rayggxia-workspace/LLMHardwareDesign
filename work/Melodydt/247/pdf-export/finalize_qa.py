"""Finalize evidence after manual inspection of all seven final-page PNGs.

This script validates existing artifacts and does not regenerate the PDF or
invoke the artifact-operation marker. Manual visual findings are explicit.
"""
import hashlib
import json
from pathlib import Path

from PIL import Image
import pdfplumber
from pypdf import PdfReader

HERE = Path(__file__).resolve().parent


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    qa_path = HERE / "qa.json"
    qa = json.loads(qa_path.read_text(encoding="utf-8"))
    pdf = Path(qa["pdf_file"])
    assert sha256(pdf) == qa["pdf_sha256"]
    assert sha256(qa["source_file"]) == qa["source_sha256"]
    reader = PdfReader(str(pdf))
    assert len(reader.pages) == qa["pages"] == 7
    fonts = {}
    for page in reader.pages:
        for ref in page["/Resources"]["/Font"].values():
            font = ref.get_object()
            name = str(font["/BaseFont"]).lstrip("/")
            desc = font.get("/FontDescriptor")
            embedded = bool(desc and any(k in desc.get_object() for k in ("/FontFile", "/FontFile2", "/FontFile3")))
            fonts[name] = {"embedded": embedded, "subtype": str(font["/Subtype"])}
    with pdfplumber.open(pdf) as plumb:
        used = sorted({c["fontname"] for page in plumb.pages for c in page.chars})
    for name in used:
        assert fonts[name]["embedded"], ("Unembedded used font", name)
    pngs = []
    for number in range(1, qa["pages"] + 1):
        path = HERE / ("final-page-%d.png" % number)
        with Image.open(path) as im:
            assert im.width >= 990 and im.height >= 1400
            dims = [im.width, im.height]
        pngs.append({"page": number, "path": str(path), "sha256": sha256(path), "pixels": dims})
    qa["font_embedding"] = {"used_fonts": used, "all_used_fonts_embedded": True, "resources": fonts}
    qa["rendering"] = {
        "tool": "Poppler pdftoppm", "dpi": 120,
        "command": "pdftoppm -r 120 -png <pdf_file> <pdf-export>/final-page",
        "exit_code": 0, "exec_chunk_id": "636bce", "pages": pngs,
    }
    qa["visual_review"] = {
        "status": "passed", "method": "Each final-page-1.png through final-page-7.png opened and visually inspected individually",
        "pages_reviewed": list(range(1, 8)),
        "checks": ["Readable embedded Chinese glyphs", "No missing-glyph boxes", "No clipped text or table cells", "No overlapping content", "Code boxes complete", "Headers and page numbers correct"],
        "review_date_local": "2026-11-09", "timezone": "Asia/Shanghai",
    }
    qa["script_sha256"] = {name: sha256(HERE / name) for name in ("export_pdf.py", "finalize_qa.py")}
    qa["scope"] = "Full conversion of the frozen implementation document only; no new token/s conclusion or experiment added."
    qa_path.write_text(json.dumps(qa, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "passed", "pages": len(reader.pages), "pdf_sha256": sha256(pdf), "qa_sha256": sha256(qa_path), "used_fonts": used}, ensure_ascii=False))


if __name__ == "__main__":
    main()
