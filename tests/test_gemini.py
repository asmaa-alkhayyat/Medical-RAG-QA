import os
from dotenv import load_dotenv
from google import genai


def test_gemini():
    load_dotenv()

    api_key = os.getenv("GEMINI_API_KEY")
    model_name = os.getenv("GEMINI_MODEL")

    if not api_key:
        print("GEMINI_API_KEY is empty. Check your .env file.")
        return
    if not model_name:
        print("GEMINI_MODEL is empty. Check your .env file.")
        return

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=model_name,
        contents="قل مرحبا",
    )
    print(response.text)


if __name__ == "__main__":
    test_gemini()