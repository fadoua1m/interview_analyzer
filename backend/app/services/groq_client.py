import random
import time

from groq import Groq
from app.config import settings


def generate(prompt: str) -> str:
    if not settings.groq_api_key:
        raise RuntimeError("Missing GROQ_API_KEY in environment")

    max_retries = settings.groq_max_retries
    base_delay = settings.groq_retry_base_delay_sec
    client = Groq(api_key=settings.groq_api_key)

    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=settings.groq_model,
                messages=[
                    {"role": "user", "content": prompt},
                ],
                temperature=0,
            )

            text = (response.choices[0].message.content or "").strip()
            if text:
                return text

            raise RuntimeError("Groq returned an empty response")

        except Exception:
            if attempt == max_retries - 1:
                raise
            delay = base_delay * (2 ** attempt) + random.uniform(0.0, 0.2)
            time.sleep(delay)

    raise RuntimeError("Groq generation failed after retries")
