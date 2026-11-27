import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT / "src"))

from rag_chain import answer_question

TESTS = [
    {"question": "What is the treatment of severe hypoglycaemia?",
     "must_contain": ["50%", "glucose", "page 19)"]},
    {"question": "ما علاج انخفاض السكر الشديد؟",
     "must_contain": ["page 19)"]},
    {"question": "When should an ESA be given for anemia in CKD?",
     "must_contain": ["10 g/dl", "page 8)"]},
    {"question": "ما الجرعة الأولية للأنسولين متوسط المفعول؟",
     "must_contain": ["10", "page 29)"]},
    {"question": "How do you test for loss of protective sensation in the diabetic foot?",
     "must_contain": ["monofilament", "tuning fork", "page 32)"]},
    {"question": "What are the indications to initiate kidney replacement therapy?",
     "must_contain": ["hyperkalemia", "page 10)"]},
    {"question": "In the CKD heatmap, what is the risk level for G1 with severely increased albuminuria (A3)?",
     "must_contain": ["orange", "page 4)"]},
    {"question": "What is the starting dose of metformin?",
     "must_contain": ["500 mg"]},
    {"question": "What is the recommended dose of amoxicillin for a child with an ear infection?",
     "must_contain": ["could not find"],
     "must_not_contain": ["page "]},
    {"question": "ما أعراض التهاب الزائدة الدودية؟",
     "must_contain": ["could not find"],
     "must_not_contain": ["page "]},
]


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")

    passed = 0
    for test in TESTS:
        answer, chunks = answer_question(test["question"])
        answer_lower = answer.lower()

        problems = []
        for word in test["must_contain"]:
            if word.lower() not in answer_lower:
                problems.append("missing: " + word)
        for word in test.get("must_not_contain", []):
            if word.lower() in answer_lower:
                problems.append("should not contain: " + word)

        if len(problems) == 0:
            passed = passed + 1
            print("PASS |", test["question"])
        
        else:
            print("FAIL |", test["question"], "|", problems)
            print("---- ANSWER ----")
            print(answer)
            print("----------------")

        time.sleep(5)   

    print("\nPassed", passed, "of", len(TESTS))