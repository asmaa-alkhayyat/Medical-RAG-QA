import re
from pathlib import Path
import pymupdf

PDF_DIR = Path(__file__).resolve().parent.parent / "data" / "pdfs"


def table_extraction(page):
    markdown_tables = []

    for table in page.find_tables().tables:
        rows = []
        for row in table.rows:
            cells = []
            for cell_box in row.cells:
                if cell_box is None:
                    cells.append("")
                else:
                    cells.append(" ".join(page.get_text(clip=cell_box).split()).replace("••", "•"))
            rows.append(cells)

        if not rows:
            continue

        header = "| " + " | ".join(rows[0]) + " |"
        separator = "|" + "---|" * len(rows[0])
        body = ["| " + " | ".join(row) + " |" for row in rows[1:]]
        markdown_tables.append("\n".join([header, separator] + body))

    return markdown_tables


def table_text_comparison():
    for pdf_path in sorted(PDF_DIR.glob("*.pdf")):
        doc = pymupdf.open(pdf_path)
        print(f"\n==================== {pdf_path.name} ====================")

        for page_num, page in enumerate(doc, start=1):
            markdown_tables = table_extraction(page)
            if not markdown_tables:
                continue

            page_text = page.get_text().lower()
            page_words = set(re.findall(r"[a-z]+", page_text))
            page_numbers = set(re.findall(r"\d+(?:\.\d+)?", page_text))

            for table_number, markdown in enumerate(markdown_tables, start=1):
                table_text = markdown.lower()
                suspicious_words = sorted(set(re.findall(r"[a-z]+", table_text)) - page_words)
                suspicious_numbers = sorted(set(re.findall(r"\d+(?:\.\d+)?", table_text)) - page_numbers)
                print(f"page {page_num} | table {table_number} | words: {suspicious_words} | numbers: {suspicious_numbers}")

if __name__ == "__main__":
    table_text_comparison()
