import json
import os
import time
from pathlib import Path
import pymupdf
from dotenv import load_dotenv
from google import genai
from google.genai import types
from page_router import PDF_DIR

ROOT = Path(__file__).resolve().parent.parent
JSON_PATH = ROOT / "data" / "extracted_content.json"
OUTPUT_DIR = ROOT / "data" / "vision description"
SECONDS_BETWEEN_REQUESTS = 5

PROMPT = """You are helping build a medical document search system.
Below is the image of one PDF page, and the text that was already extracted from it by code.

Describe ONLY the visual parts of this page (diagrams, figures, photos, tables shown as images).
Do not repeat the normal paragraphs, side panels, text boxes or bullet lists of the page:
their words are already in the extracted text. A box that contains only a title and a bullet list is normal text, so skip it.
Exception: if the page has a FLOWCHART, follow the SIDE PANELS AND NOTES rule in part A.

For every figure, table or photo, start with its title or caption exactly as printed on the page,
for example "Figure 3. Algorithm for evaluation and management of anemia in CKD. ESA: erythropoiesis-stimulating agent."
Write it on its own first line, then write the description under it.
If there is no printed title, write "No title".

First decide what kind of visual it is:

A) FLOWCHART: boxes connected by drawn arrows or lines.
   Rules for boxes:
   - Every rectangle drawn with its own outline is ONE box, even if it contains several lines, paragraphs or a heading.
     Never split one outlined rectangle into several boxes. Two separate outlines are two boxes, even if they touch.
   Rules for arrows:
   - Write an arrow only if you can see it drawn in the image. Never connect two boxes only because they are close
     or because they seem related.
   - A box with no arrow leaving it is an END of the flow. Check this for every box before you write an arrow from it.
   - If one arrow splits into several arrows, write every one of them.
   - Look for long arrows along the edge of the chart and for arrows that merge into another arrow, and write them too.
   - Boxes placed side by side in the same row are NOT connected to each other, unless an arrow is drawn between them.
     An arrow that goes down into a row starts from the box ABOVE that row. Look at where each arrow really starts.
   Do these steps in order:
   STEP 1 - BOXES: number every box and copy ALL of its text exactly, including a heading line
      such as "REVIEW IN 3 MONTHS" and condition lines such as "If goal not achieved".
   STEP 2 - ARROWS: list every arrow, one per line, as "Box A -> Box B".
      Write a label ONLY if the word Yes or No is printed next to that arrow in the image,
      for example "Box 3 -> [Yes] -> Box 4".
      An arrow with no printed label is a plain arrow "Box A -> Box B".
      Never guess or invent a Yes/No branch. Not every box is a decision.
   Do not write a summary or any explanation after STEP 2, except the following section.
   SIDE PANELS AND NOTES (only on a page with a flowchart): after STEP 2, write this heading on its own line,
      then copy as clean text, in reading order, every side panel next to the flowchart (its title, then its items),
      every small table, and every footnote with its marker (# * ** †), exactly as printed.
      Keep each footnote as one complete sentence. Do not put flowchart words inside them.

B) GROUP DIAGRAM: a title or central shape with items around it or under it, and no connecting arrows or lines.
   Bullet marks such as arrows (➢) or dots are NOT flow arrows.
   Write an outline: the title, then each group with its items below it. Do not write any arrows for this kind.

C) TABLE shown as an image: write it as a Markdown table.
   - Every row must have the same number of columns as the header. Keep every row label and column label.
   - A heading that covers several columns is written once, on a line above the table.
   - If one cell covers several rows or columns (a merged cell), repeat its full text in each row or column it covers.
     Never split the items of one cell across different rows.
   - Fill the table column by column. Use the horizontal lines to see which rows each cell covers.
     Never copy the text of one column into another column.
   - If cells are colored (for example a heatmap), write the color and its meaning from the legend
     in the caption inside each cell, for example "green (low risk)".
   If the page has several tables, write each one separately, even if they touch each other.

D) PHOTO or DRAWING: write the caption, then any short text (one to three lines) printed right next to the picture
   that explains it, copied exactly from the extracted text (for example "Dorsal pedis: Feel in the middle of the
   dorsum of the foot ..."). Then write one plain sentence about what is visible. Do not diagnose.
   Do not copy long paragraphs. Do not count marks, spots or arrows unless they are numbered or labeled.

Rules:
- Copy words and numbers exactly as they appear in the page text. Never change or guess a number.
- Plain text only. Do not use LaTeX. Write symbols exactly as printed (for example ≥ ≤ ± < >).
- Ignore logos, decoration, page headers and footers.
- Ignore the article citation box, dates, license text and the references or resources list.
- Do not add any medical information that is not on the page.

Text already extracted from this page:
-----
{page_text}
-----
"""

def ask_gemini(client, model_name, contents):
    # sends one request, tries up to 3 times
    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=contents,
                config=types.GenerateContentConfig(temperature=0),
            )
            if response.text:
                return response.text
            print("  EMPTY answer")
            return None
        except Exception as error:
            print("  FAILED (try", attempt + 1, "of 3):", error)
            time.sleep(20)
    return None


def describe_vision_pages():
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    model_name = os.getenv("GEMINI_MODEL")
    if not api_key or not model_name:
        print("Check GEMINI_API_KEY and GEMINI_MODEL in your .env file.")
        return

    client = genai.Client(api_key=api_key)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with open(JSON_PATH, encoding="utf-8") as f:
        items = json.load(f)

    vision_pages = []
    for item in items:
        if item["type"] == "text" and item["needs_vision"]:
            vision_pages.append(item)

    print("Pages marked needs_vision in the JSON:", len(vision_pages))
    for item in vision_pages:
        print("  ", item["source"], "page", item["page"])

    for item in vision_pages:
        file_name = item["source"]
        page_num = item["page"]
        stem = Path(file_name).stem
        output_file = OUTPUT_DIR / f"{stem}_p{page_num:02d}.txt"

        if output_file.exists():
            continue

        # Draw page as an image
        doc = pymupdf.open(PDF_DIR / file_name)
        image_bytes = doc[page_num - 1].get_pixmap(dpi=150).tobytes("png")
        doc.close()
        image_part = types.Part.from_bytes(data=image_bytes, mime_type="image/png")

        print("Describing", file_name, "page", page_num, "...")
        prompt = PROMPT.format(page_text=item["content"])
        description = ask_gemini(client, model_name, [image_part, prompt])
        time.sleep(SECONDS_BETWEEN_REQUESTS)
        if description is None:
            continue

        output_file.write_text(description, encoding="utf-8")

    missing = []
    for item in vision_pages:
        output_file = OUTPUT_DIR / f"{Path(item['source']).stem}_p{item['page']:02d}.txt"
        if not output_file.exists():
            missing.append((item["source"], item["page"]))

    if missing:
        print("\nMISSING descriptions for:", missing)
        print("Run the script again to retry them.")
    else:
        print("\nOK: all", len(vision_pages), "pages have a saved description in", OUTPUT_DIR)


if __name__ == "__main__":
    describe_vision_pages()
    