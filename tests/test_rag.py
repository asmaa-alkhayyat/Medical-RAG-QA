import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT / "src"))

from rag_chain import answer_question


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")

    question = "What is the starting dose of metformin?"

    answer, chunks = answer_question(question)

    print("QUESTION:", question)
    print("\nANSWER:\n", answer)
    print("\nCHUNKS SENT TO GEMINI:")
    for chunk in chunks:
        print(" -", chunk["source"][:35], "| page", chunk["page"], "| distance", round(chunk["distance"], 3))