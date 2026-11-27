import re
import unicodedata
import pymupdf
from page_router import page_router, PDF_DIR


def fix_ligatures(text):
    new_text = ""
    for character in text:
        name = unicodedata.name(character, "")
        if "LIGATURE" in name:
            new_text += unicodedata.normalize("NFKC", character)
        else:
            new_text += character
    return new_text


def fix_double_bullets(text):
    return text.replace("••", "•")


def fix_broken_words(text, words_in_file):
    broken_word_parts = set(re.findall(r"([A-Za-z]+)-\s+([a-z]+)", text))

    for first_part, second_part in broken_word_parts:
        whole_word = first_part + second_part
        if whole_word.lower() in words_in_file:
            text = re.sub(r"\b" + first_part + r"-\s+" + second_part, whole_word, text)

    return text


def normalize_line(line):
    return re.sub(r"\d+", "#", line.strip())


def find_repeated_lines(page_texts):
    counts = {}
    for text in page_texts:
        lines = text.strip().split("\n")
        edge_lines = lines[:3] + lines[-3:]
        keys_in_this_page = set()
        for line in edge_lines:
            key = normalize_line(line)
            if len(key) >= 5:
                keys_in_this_page.add(key)
        for key in keys_in_this_page:
            counts[key] = counts.get(key, 0) + 1

    repeated_lines = set()
    for key, count in counts.items():
        if count >= 3 and count >= 0.3 * len(page_texts):
            repeated_lines.add(key)
    return repeated_lines


def remove_headers_footers(text, repeated_lines):
    kept_lines = []
    for line in text.split("\n"):
        if normalize_line(line) not in repeated_lines:
            kept_lines.append(line)
    return "\n".join(kept_lines)






def clean_text(text, words_in_file):
    text = fix_ligatures(text)
    text = fix_double_bullets(text)
    text = fix_broken_words(text, words_in_file)
    return text

def show_cleaning_results():
    decisions = page_router(print_report=False)

    for pdf_path in sorted(PDF_DIR.glob("*.pdf")):
        doc = pymupdf.open(pdf_path)

        pages = {}
        for page_num, (action, content_end_char) in decisions[pdf_path.name].items():
            if action == "text" or action == "vision":
                text = doc[page_num - 1].get_text()
               
                if content_end_char is not None:
                    text = text[:content_end_char]
                pages[page_num] = text

        
        all_text = " ".join(pages.values()).lower()
        words_in_file = set(re.findall(r"[a-z]+", all_text))

        print(f"\n=== CLEANING: {pdf_path.name} ===")

        for page_num, text in pages.items():

            # fix_ligatures
            for position in range(len(text)):
                character = text[position]
                if "LIGATURE" in unicodedata.name(character, ""):
                    start = max(0, position - 10)
                    example = text[start : position + 10].replace("\n", " ")
                    print(f"  page {page_num} | ligature | BEFORE: {example} | AFTER: {fix_ligatures(example)}")

            # fix_double_bullets
            position = text.find("••")
            if position != -1:
                start = max(0, position - 5)
                example = text[start : position + 25].replace("\n", " ")
                print(f"  page {page_num} | double bullets | BEFORE: {example} | AFTER: {fix_double_bullets(example)}")

            # fix_broken_words
            pairs = set(re.findall(r"([A-Za-z]+)-\s+([a-z]+)", text))
            for first_part, second_part in pairs:
                whole_word = first_part + second_part
                if whole_word.lower() in words_in_file:
                    print(f"  page {page_num} | broken word | BEFORE: {first_part}- {second_part} | AFTER: {whole_word}")

                    
if __name__ == "__main__":
    show_cleaning_results()


