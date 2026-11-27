import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INPUT_JSON = ROOT / "data" / "final_content.json"
OUTPUT_JSON = ROOT / "data" / "chunks.json"

TARGET_CHARS = 1000      
MAX_CHARS = 1500         


def split_text(text):
    pieces = []
    current_lines = []
    current_size = 0

    for line in text.split("\n"):
        current_lines.append(line)
        current_size = current_size + len(line) + 1

        ends_sentence = line.rstrip().endswith(".")
        if (current_size >= TARGET_CHARS and ends_sentence) or current_size >= MAX_CHARS:
            pieces.append("\n".join(current_lines))
            current_lines = [line]          
            current_size = len(line) + 1


    if len(current_lines) > 1 or not pieces:
        pieces.append("\n".join(current_lines))

    return pieces


def chunk_content():
    with open(INPUT_JSON, encoding="utf-8") as file:
        items = json.load(file)

    chunks = []
    for item in items:
        if item["type"] == "text":
            pieces = split_text(item["content"])      
        else:
            pieces = [item["content"]]                

        for piece in pieces:
            piece = piece.strip()
            if piece == "":
                continue
            chunks.append({
                "chunk_id": f"chunk_{len(chunks) + 1:03d}",
                "source": item["source"],
                "page": item["page"],
                "type": item["type"],
                "image_path": item.get("image_path", ""),
                "text": piece,
            })

    with open(OUTPUT_JSON, "w", encoding="utf-8") as file:
        json.dump(chunks, file, ensure_ascii=False, indent=2)

    print("Chunks:", len(chunks))
    for chunk_type in ["text", "table", "diagram"]:
        sizes = [len(c["text"]) for c in chunks if c["type"] == chunk_type]
        print(f"  {chunk_type}: {len(sizes)} chunks, shortest {min(sizes)}, longest {max(sizes)} characters")
    print("Saved:", OUTPUT_JSON)


if __name__ == "__main__":
    chunk_content()