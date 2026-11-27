import json
from pathlib import Path

import pymupdf

from page_router import PDF_DIR

ROOT = Path(__file__).resolve().parent.parent
INPUT_JSON = ROOT / "data" / "extracted_content.json"
VISION_DIR = ROOT / "data" / "vision description"
IMAGES_DIR = ROOT / "data" / "diagram_images"
OUTPUT_JSON = ROOT / "data" / "final_content.json"

# Label words to delete
LABEL_WORDS = ["FLOWCHART", "GROUP DIAGRAM", "TABLE", "PHOTO", "DRAWING"]

# Fix wrong words
TEXT_TYPOS = [
    ("20–50 mI", "20–50 ml"),
    ("NaCI", "NaCl"),
    ("Iimited", "limited"),
]

ARROWS_WARNING = "Note: the arrows were extracted automatically and may contain errors. Check the original page image."

# Key: (file name, page). Value: list of (wrong text, correct text).
MANUAL_FIXES = {
    # Diabetes : p16
    ("Diagnosis and Management of Type 2 Diabetes.pdf", 16): [
        ("Box 7 -> Box 8\n", ""),
        ("Box 31 -> Box 34\n", ""),

        ("diagnosis\n34. REVIEW IN 1 MONTH\n35. REVIEW IN 3 MONTHS (or immediately if symptoms appear)\n36. IF goal not achieved",
         "diagnosis\nREVIEW IN 1 MONTH\n34. REVIEW IN 3 MONTHS (or immediately if symptoms appear)\n35. IF goal not achieved"),

        ("Box 35 -> Box 36", "Box 34 -> Box 35"),
        ("Box 29 -> Box 35", "Box 29 -> Box 34"),
    ],
    # Diabetes: p29
    ("Diagnosis and Management of Type 2 Diabetes.pdf", 29): [
        ("Box 8 -> Box 9", "Box 5 -> Box 9"),
    ],

    # Kidney: p4
    ("Care of Adults with Advanced Chronic Kidney Disease.pdf", 4): [
        ("G1 ≥ 90 | green (low risk) | yellow (moderately increased) | yellow (moderately increased)",
         "G1 ≥ 90 | green (low risk) | yellow (moderately increased) | orange (high)"),
    ],
    # Kidney: p6
    ("Care of Adults with Advanced Chronic Kidney Disease.pdf", 6): [
        ("UACR > 200 mg/g ** | People with T2D with cardiovascular disease | People with chronic coronary disease |",
         "UACR > 200 mg/g ** | People with T2D with cardiovascular disease | People with heart failure with reduced, preserved, or minimally reduced ejection fraction; people with chronic coronary disease |"),
    ],
}


def clean_vision_description(description):
    kept_lines = []
    for line in description.split("\n"):
        line = line.rstrip()

        # Skip label lines
        is_label = False
        if line.strip()[:2] in ["A)", "B)", "C)", "D)"]:
            for word in LABEL_WORDS:
                if word in line.upper():
                    is_label = True
        if is_label:
            continue

        # Delete the icon description 
        if "(icon of" in line:
            line = line[:line.index("(icon of")].rstrip()

        kept_lines.append(line)

    text = "\n".join(kept_lines).strip()

    # Delete empty notes section 
    heading = "SIDE PANELS AND NOTES"
    position = text.find(heading)
    if position != -1 and text[position + len(heading):].strip() == "(None)":
        text = text[:position].strip()

    while "\n\n\n" in text:
        text = text.replace("\n\n\n", "\n\n")

    return text


def normalize(text):
    text = text.replace("²", "2")
    return "".join(text.split())   


def remove_duplicate_lines(items):
    removed_count = 0
    for text_item in items:
        if text_item["type"] != "text":
            continue
        for diagram_item in items:
            same_file = diagram_item["source"] == text_item["source"]
            same_page = diagram_item["page"] == text_item["page"]
            if diagram_item["type"] == "diagram" and same_file and same_page:
                description_one_line = normalize(diagram_item["content"])
                kept_lines = []
                for line in text_item["content"].split("\n"):
                    line_one_line = normalize(line)
                    if line_one_line != "" and line_one_line in description_one_line:
                        removed_count = removed_count + 1
                    else:
                        kept_lines.append(line)
                text_item["content"] = "\n".join(kept_lines)
    print("Duplicate lines removed from text items:", removed_count)



def merge_vision():
    with open(INPUT_JSON, encoding="utf-8") as file:
        items = json.load(file)

    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    final_items = []
    missing = []

    for item in items:
        for wrong_text, correct_text in TEXT_TYPOS:
            item["content"] = item["content"].replace(wrong_text, correct_text)
        if not item["needs_vision"]:
            final_items.append(item)
            continue

        file_name = item["source"]
        page_num = item["page"]
        stem = Path(file_name).stem
        description_file = VISION_DIR / f"{stem}_p{page_num:02d}.txt"
        if not description_file.exists():
            missing.append(f"{file_name} page {page_num}")
            final_items.append(item)
            continue

        description = clean_vision_description(description_file.read_text(encoding="utf-8"))
        for wrong_text, correct_text in TEXT_TYPOS:
            description = description.replace(wrong_text, correct_text)

        # Errors fixed by hand
        for wrong_text, correct_text in MANUAL_FIXES.get((file_name, page_num), []):
            if wrong_text in description:
                description = description.replace(wrong_text, correct_text)
            else:
                print("WARNING: manual fix not found in", file_name, "page", page_num, "->", wrong_text[:40])

        if "STEP 2" in description:
            description = description + "\n\n" + ARROWS_WARNING

        # Save page image
        image_file = IMAGES_DIR / f"{stem}_p{page_num:02d}.png"
        if not image_file.exists():
            pdf = pymupdf.open(PDF_DIR / file_name)
            image_bytes = pdf[page_num - 1].get_pixmap(dpi=200).tobytes("png")
            pdf.close()
            image_file.write_bytes(image_bytes)

        if "SIDE PANELS AND NOTES" in description:
            print("Page", page_num, "of", file_name, ": the text item is replaced by the clean description")
        else:
            final_items.append(item)

        final_items.append({
            "source": file_name,
            "page": page_num,
            "type": "diagram",
            "needs_vision": False,
            "image_path": f"data/diagram_images/{image_file.name}",
            "content": description,
        })



    remove_duplicate_lines(final_items)

    with open(OUTPUT_JSON, "w", encoding="utf-8") as file:
        json.dump(final_items, file, ensure_ascii=False, indent=2)

    diagram_count = sum(1 for item in final_items if item["type"] == "diagram")
    print("Items:", len(final_items), "| diagram items:", diagram_count)
    if missing:
        print("MISSING descriptions:", missing)
    print("Saved:", OUTPUT_JSON)


if __name__ == "__main__":
    merge_vision()