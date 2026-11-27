import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT / "src"))
sys.path.append(str(ROOT / "tests"))

from rag_chain import answer_question
from test_questions import TESTS


if __name__ == "__main__":
    output_file = open(ROOT / "answers.txt", "w", encoding="utf-8")

    number = 1
    for test in TESTS:
        answer, chunks = answer_question(test["question"])

        output_file.write("=" * 60 + "\n")
        output_file.write("QUESTION " + str(number) + ": " + test["question"] + "\n\n")
        output_file.write(answer + "\n\n")

        print("Done question", number)
        number = number + 1
        time.sleep(5)

    output_file.close()
    print("Saved answers.txt")