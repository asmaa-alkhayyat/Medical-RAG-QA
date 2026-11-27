import sys
from pathlib import Path
import chromadb

ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT / "src"))

from embeddings import embed_texts

DB_FOLDER = ROOT / "chroma_db"
COLLECTION_NAME = "medical_chunks"
RESULTS_PER_QUESTION = 5

QUESTIONS = [
    "What is the treatment of severe hypoglycaemia?",
    "ما علاج انخفاض السكر الشديد؟",
    "When should an ESA be given for anemia in CKD?",
    "ما هي مؤشرات بدء العلاج الكلوي البديل؟",
    "How do you test for loss of protective sensation in the diabetic foot?",
    "ما الجرعة الأولية للأنسولين متوسط المفعول؟",
]


def test_retrieval():
    sys.stdout.reconfigure(encoding="utf-8")   

    client = chromadb.PersistentClient(path=str(DB_FOLDER))
    collection = client.get_collection(COLLECTION_NAME)

    for question in QUESTIONS:
        print("=" * 70)
        print("QUESTION:", question)

        question_vector = embed_texts([question])
        results = collection.query(
            query_embeddings=question_vector,
            n_results=RESULTS_PER_QUESTION,
        )

        for i in range(RESULTS_PER_QUESTION):
            text = results["documents"][0][i]
            metadata = results["metadatas"][0][i]
            distance = results["distances"][0][i]

            print("\n  Result", i + 1)
            print("  File:", metadata["source"][:35], "| page:", metadata["page"], "| type:", metadata["type"])
            print("  Distance:", round(distance, 3), "(smaller = closer)")
            print("  Text:", text.replace("\n", " "))

if __name__ == "__main__":
    test_retrieval()