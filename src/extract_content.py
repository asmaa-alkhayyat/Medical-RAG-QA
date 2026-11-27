import json
import re
import pymupdf
from pathlib import Path
from page_router import page_router, PDF_DIR, CONTENT_STARTS, REF_HEADING
from table_text_comparison import table_extraction
from text_cleaning import clean_text, find_repeated_lines, remove_headers_footers

OUTPUT_FILE = Path(__file__).resolve().parent.parent / "data" / "extracted_content.json"
NOTES_DISTANCE = 40
NOTES_CHAIN_DISTANCE = 5
NOTE_START = re.compile(r"^\s*(\*|†|‡|§|Note|Source|Abbreviation)", re.IGNORECASE)
BLOCKS_TO_DROP = {
    "Care of Adults with Advanced Chronic Kidney Disease.pdf": {
             1: ["Citation:", "Malhotra", "Adults with Advanced Chronic", "4378.", "jcm13154378",
            "Academic Editor", "In this article, we provide", "Received:", "Revised:",
            "Accepted:", "Published:", "Copyright:", "Licensee", "This article is an open access",
            "distributed", "Figure 1.", "4.0/)", "J. Clin. Med.", "https://www.mdpi.com","Kidney Disease. J. Clin.","conditions of the Creative", "Attribution (CC BY)","creativecommons.org"],
    },
}


def extract_content():
    decisions = page_router(print_report=False)
    all_items = []

    for pdf_path in sorted(PDF_DIR.glob("*.pdf")):
        doc = pymupdf.open(pdf_path)


        words_in_file = set()
        for page in doc:
            words_in_file.update(re.findall(r"[A-Za-z]+", page.get_text()))

        # Find repeated lines
        all_page_texts = []
        for page in doc:
            all_page_texts.append(page.get_text())
        repeated_lines = find_repeated_lines(all_page_texts)
        print(pdf_path.name, "repeated lines:", repeated_lines)

        # Page router
        for page_num, (action, content_end_char) in decisions[pdf_path.name].items():
            if action == "review":
                print("REVIEW this page:", pdf_path.name, "page", page_num)

            if action not in ("text", "vision"):
                continue

            page = doc[page_num - 1]

            # Find tables
            tables_markdown = []
            table_boxes = []
            if action == "text":
                tables_markdown = table_extraction(page)
                for table in page.find_tables().tables:
                    table_boxes.append(pymupdf.Rect(table.bbox))

            # Find notes 
            kept_blocks = []
            table_notes = []
            table_bottoms = []
            for box in table_boxes:
                table_notes.append("")
                table_bottoms.append(box.y1)
           
            drop_starts = BLOCKS_TO_DROP.get(pdf_path.name, {}).get(page_num, [])


            for block in page.get_text("blocks", sort=True):
                block_box = pymupdf.Rect(block[:4])
                block_text = remove_headers_footers(block[4], repeated_lines)

                # page number: a block with only a number at the top or bottom of the page
                at_page_edge = block_box.y0 > page.rect.height * 0.9 or block_box.y1 < page.rect.height * 0.1
                if block_text.strip() == "" or (block_text.strip().isdigit() and at_page_edge):
                    continue

                is_dropped = False
                for start in drop_starts:
                    if block_text.strip().startswith(start):
                        is_dropped = True
                if is_dropped:
                    continue

                center = (block_box.tl + block_box.br) / 2
                inside_table = False
                note_of_table = None
                for number, box in enumerate(table_boxes):
                    if box.contains(center):
                        inside_table = True
                    distance_below = block_box.y0 - table_bottoms[number]
                    overlaps_table_width = block_box.x0 < box.x1 and block_box.x1 > box.x0

                    if table_notes[number] == "":
                        allowed_distance = NOTES_DISTANCE
                        looks_like_note = NOTE_START.match(block_text) is not None
                    else:
                        allowed_distance = NOTES_CHAIN_DISTANCE
                        looks_like_note = True
                    if looks_like_note and -2 <= distance_below <= allowed_distance and overlaps_table_width:
                        note_of_table = number

                if inside_table:
                    continue
                if note_of_table is not None:
                    table_notes[note_of_table] += block_text
                    table_bottoms[note_of_table] = block_box.y1
                else:
                    kept_blocks.append(block_text)
            page_text = "".join(kept_blocks)

            # notes under each table join the table itself
            for number in range(len(tables_markdown)):
                if table_notes[number].strip():
                    tables_markdown[number] += "\n\nNotes:\n" + table_notes[number].strip()

            # 3) remove references and cut the start of the page
            if content_end_char is not None:
                heading = REF_HEADING.search(page_text)
                if heading:
                    page_text = page_text[:heading.start()]

            start_word = CONTENT_STARTS.get(pdf_path.name, {}).get(page_num)
            if start_word:
                position = page_text.find(start_word)
                if position != -1:
                    page_text = page_text[position:]

            # 4) clean text
            page_text = clean_text(page_text, words_in_file).strip()
            tables_markdown = [clean_text(t, words_in_file) for t in tables_markdown]

            # 5) save items
            needs_vision = (action == "vision")
            if page_text:
                all_items.append({"source": pdf_path.name, "page": page_num, "type": "text",
                                  "needs_vision": needs_vision, "content": page_text})
            for table_md in tables_markdown:
                all_items.append({"source": pdf_path.name, "page": page_num, "type": "table",
                                  "needs_vision": needs_vision, "content": table_md})

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_items, f, ensure_ascii=False, indent=2)

    print("Saved", len(all_items), "items to", OUTPUT_FILE)
    for pdf_path in sorted(PDF_DIR.glob("*.pdf")):
        texts = [i for i in all_items if i["source"] == pdf_path.name and i["type"] == "text"]
        tables = [i for i in all_items if i["source"] == pdf_path.name and i["type"] == "table"]
        vision = [i["page"] for i in texts if i["needs_vision"]]
        print(pdf_path.name, "| text pages:", len(texts), "| tables:", len(tables), "| vision pages:", vision)


if __name__ == "__main__":
    extract_content()