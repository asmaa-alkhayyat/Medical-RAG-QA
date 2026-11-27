import re
from pathlib import Path
import pymupdf

PDF_DIR = Path(__file__).resolve().parent.parent / "data" / "pdfs"

MIN_DRAWINGS = 15
MIN_IMAGES = 1
MIN_CHARS = 100
MIN_REF_HITS = 5

MANUAL_DECISIONS = {
    "Care of Adults with Advanced Chronic Kidney Disease.pdf": {
        "skip": set(),
        "text": {3},
        "vision": {1, 4, 5, 6, 8, 10, 12},
    },
    "Diagnosis and Management of Type 2 Diabetes.pdf": {
        "skip": {1, 2, 3, 4, 5, 6, 8},
        "text": {11, 12, 13, 18, 19, 22, 27, 33},
        "vision": set(),
    },
}

CONTENT_STARTS = {
    "Care of Adults with Advanced Chronic Kidney Disease.pdf": {1: "Abstract:"},
    "Diagnosis and Management of Type 2 Diabetes.pdf": {7: "Abbreviations"},
}

REF_HEADING = re.compile(r"^\s*(author contributions|references|bibliography|resources)\b", re.IGNORECASE | re.MULTILINE)
REF_MARKERS = re.compile(r"et al\.|\[CrossRef\]|\[PubMed\]|doi:|doi\.org|Geneva: World Health Organization|Licence:", re.IGNORECASE)


def page_router(print_report=True):
    decisions = {}

    for pdf_path in sorted(PDF_DIR.glob("*.pdf")):
        doc = pymupdf.open(pdf_path)
        manual = MANUAL_DECISIONS.get(pdf_path.name, {})
        results = {"skip": [], "empty": [], "review": [], "references": [], "vision": [], "text": []}
        decisions[pdf_path.name] = {}

        if print_report:
            print(f"\n=== {pdf_path.name} ===")
       
        for page_num, page in enumerate(doc, start=1):
            content_end_char = None

            if page_num in manual.get("skip", set()):
                action = "skip"
            elif page_num in manual.get("vision", set()):
                action = "vision"
            elif page_num in manual.get("text", set()):
                action = "text"
            else:
                text = page.get_text()
                chars = len(text.strip())
                drawings = len(page.get_drawings())
                images = len(page.get_images())
                heading = REF_HEADING.search(text)

                if chars == 0 and drawings == 0 and images == 0:
                    action = "empty"
                elif chars < MIN_CHARS:
                    action = "review"
                elif heading and heading.start() < 300:
                    action = "references"
                elif not heading and len(REF_MARKERS.findall(text)) >= MIN_REF_HITS:
                    action = "references"
                else:
                    if heading:
                        content_end_char = heading.start()
                    if drawings >= MIN_DRAWINGS or images >= MIN_IMAGES:
                        action = "vision"
                    else:
                        action = "text"

            results[action].append(page_num)
            decisions[pdf_path.name][page_num] = (action, content_end_char)
            if content_end_char is not None:
                text = page.get_text()
                if print_report:
                    print(f"  page {page_num}: content ends at character {content_end_char}")
                    print(f"    LAST KEPT : ...{text[max(0, content_end_char - 150) : content_end_char]!r}")
                    print(f"    FIRST CUT : {text[content_end_char : content_end_char + 150]!r}...")
       
        for action, pages in results.items():
            if print_report:
                print(f"{action:>10}: {pages}")

    return decisions


if __name__ == "__main__":
    page_router()