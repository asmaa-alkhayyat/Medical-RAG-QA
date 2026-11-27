import json
from pathlib import Path
import chromadb
from embeddings import embed_texts

ROOT = Path(__file__).resolve().parent.parent
INPUT_JSON = ROOT / "data" / "chunks.json"
DB_FOLDER = ROOT / "chroma_db"
COLLECTION_NAME = "medical_chunks"


def build_index():
    with open(INPUT_JSON, encoding="utf-8") as file:
        chunks = json.load(file)

    ids = []
    texts = []
    metadatas = []
    for chunk in chunks:
        ids.append(chunk["chunk_id"])
        texts.append(chunk["text"])
        metadatas.append({
            "source": chunk["source"],
            "page": chunk["page"],
            "type": chunk["type"],
            "image_path": chunk["image_path"],
        })

    print("Creating vectors for", len(texts), "chunks (this may take a few minutes)...")
    vectors = embed_texts(texts)

    client = chromadb.PersistentClient(path=str(DB_FOLDER))

    # Delete the old collection when run again
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass

    collection = client.create_collection(
        COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )
    collection.add(
        ids=ids,
        embeddings=vectors,
        documents=texts,
        metadatas=metadatas,
    )

    print("Chunks saved in the database:", collection.count())
    print("Database folder:", DB_FOLDER)


if __name__ == "__main__":
    build_index()