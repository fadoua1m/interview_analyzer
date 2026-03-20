from google import genai
from google.genai import types
from app.config import settings

MODEL = "gemini-2.5-flash"


def generate(prompt: str) -> str:
    with genai.Client(api_key=settings.gemini_api_key) as client:
        response = client.models.generate_content(
            model=MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.0            ),
        )
    return response.text.strip()