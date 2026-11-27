import os
import time
from pathlib import Path
import chromadb
from dotenv import load_dotenv
from google import genai
from google.genai import types
from embeddings import embed_texts

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

DB_FOLDER = ROOT / "chroma_db"
COLLECTION_NAME = "medical_chunks"
CHUNKS_TO_USE = 8
NEIGHBORS_FOR_TOP = 4     
MAX_DISTANCE = 0.6       
NOT_FOUND_MESSAGE = "I could not find this information in the provided documents."

PROMPT_RULES = """
You are a medical document assistant.
Answer the question using ONLY the context below. Do not use any outside knowledge.
If the answer is not in the context, say exactly: "I could not find this information in the provided documents." and write nothing else.

Otherwise write the answer in this format, in the same language as the question (translate the three headings too):

Answer:
One or two clear sentences that answer the question directly. If the answer is different in different situations or on different pages, say so here (for example: "It depends on the patient's situation").

Details:
Write one group for each page of the context that answers the question. Start each group with the page number (for example "Page 16:"), then write short bullet points.
In each group, write one bullet for every box or sentence on that page that mentions the drug or treatment asked about, even if it applies to a different situation (for example a different glucose level, ketone result or symptoms). Never leave out a box because it seems more severe or less common.
Each bullet must contain the situation in which it applies, written in plain words, and the dose or action. Copy numbers exactly. Never invent doses, numbers or steps.
Explain a term like "goal" with its value from the context (for example the fasting plasma glucose or HbA1c target). If the context does not explain a term, do not guess.
If the facts come from a flowchart, describe the path in plain words (for example: "after 3 months, if the goal is not achieved, begin metformin"). Do not mention box numbers.
If the context says that a page is the simplified or the detailed version of a protocol, write that next to the page number (for example "Page 25 (simplified protocol):").

Original text:
The exact original sentences or box texts of the main facts, copied word for word from the context in quotation marks.

Do not write sources inside the text. After everything, write one last line that starts with SOURCES: followed by every page you used, each in its own parentheses, like SOURCES: (File name, page 32) (File name, page 33). Write this line in English even when the answer is in Arabic.
Do not write any note about arrows or about checking page images. The application shows that itself.
"""

def get_next_chunk_id(chunk_id):
    number = int(chunk_id.split("_")[1])     
    return f"chunk_{number + 1:03d}"        

def is_arabic(text):
    for character in text:
        if "\u0600" <= character <= "\u06FF":
            return True
    return False


def translate_to_english(client, question):
    prompt = "Translate this medical question into English. Return only the translation.\n\n" + question
    try:
        response = client.models.generate_content(
            model=os.getenv("GEMINI_MODEL"),
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0),
        )
        return response.text.strip()
   
    except Exception:
        return question      

    
def get_relevant_chunks(question):
    client = chromadb.PersistentClient(path=str(DB_FOLDER))
    collection = client.get_collection(COLLECTION_NAME)

    question_vector = embed_texts([question])
    results = collection.query(
        query_embeddings=question_vector,
        n_results=CHUNKS_TO_USE,
    )

    ids = results["ids"][0]
    texts = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    found_chunks = []
    for i in range(len(texts)):
        found_chunks.append({
            "chunk_id": ids[i],
            "text": texts[i],
            "source": metadatas[i]["source"],
            "page": metadatas[i]["page"],
            "type": metadatas[i]["type"],
            "image_path": metadatas[i]["image_path"],
            "distance": distances[i],
        })


    used_ids = list(ids)
    final_chunks = []
    for position in range(len(found_chunks)):
        chunk = found_chunks[position]
        final_chunks.append(chunk)

        if position >= NEIGHBORS_FOR_TOP or chunk["type"] != "text":
            continue

        next_id = get_next_chunk_id(chunk["chunk_id"])
        if next_id in used_ids:
            continue

        next_result = collection.get(ids=[next_id])
        if len(next_result["ids"]) == 0:
            continue

        next_metadata = next_result["metadatas"][0]
        same_file = next_metadata["source"] == chunk["source"]
        if same_file and next_metadata["type"] == "text":
            final_chunks.append({
                "chunk_id": next_id,
                "text": next_result["documents"][0],
                "source": next_metadata["source"],
                "page": next_metadata["page"],
                "type": next_metadata["type"],
                "image_path": next_metadata["image_path"],
                "distance": chunk["distance"],   
            })
            used_ids.append(next_id)

    return final_chunks


def build_prompt(question, chunks):
    context = ""
    for chunk in chunks:
        context = context + f"[Source: {chunk['source']}, page {chunk['page']}]\n"
        context = context + chunk["text"] + "\n\n"

    return f"{PROMPT_RULES}\n\nCONTEXT:\n{context}\nQUESTION: {question}\n\nANSWER:"


def answer_question(question):
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    
    search_question = question
    if is_arabic(question):
        search_question = translate_to_english(client, question)

    chunks = get_relevant_chunks(search_question)

    if not chunks or chunks[0]["distance"] > MAX_DISTANCE:
        return NOT_FOUND_MESSAGE, []

    prompt = build_prompt(question, chunks)

    answer_text = None
    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model=os.getenv("GEMINI_MODEL"),
                contents=prompt,
                config=types.GenerateContentConfig(temperature=0),
            )
            answer_text = response.text
            break
        except Exception:
            time.sleep(10)    

    if answer_text is None:
        return "The AI service is busy right now. Please try again in a minute.", chunks

    if NOT_FOUND_MESSAGE in answer_text:
        return NOT_FOUND_MESSAGE, []

    return answer_text, chunks
