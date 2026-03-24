import random
import time

from google import genai
from google.genai import types
from app.config import settings

def generate(prompt: str) -> str:
    max_retries = settings.gemini_max_retries
    base_delay = settings.gemini_retry_base_delay_sec

    for attempt in range(max_retries):
        try:
            with genai.Client(api_key=settings.gemini_api_key) as client:
                response = client.models.generate_content(
                    model=settings.gemini_model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=settings.gemini_temperature,
                    ),
                )

            text = (response.text or "").strip()
            if text:
                return text

            raise RuntimeError("Gemini returned an empty response")

        except Exception:
            if attempt == max_retries - 1:
                raise
            delay = base_delay * (2 ** attempt) + random.uniform(0.0, 0.2)
            time.sleep(delay)

    raise RuntimeError("Gemini generation failed after retries")