# app/services/gemini_service.py
from google import genai
from app.config import settings

MODEL = "gemini-2.5-flash"


def _generate(prompt: str) -> str:
    """Use context manager as per official docs to avoid httpx client closed error."""
    with genai.Client(api_key=settings.gemini_api_key) as client:
        response = client.models.generate_content(
            model=MODEL,
            contents=prompt,
        )
    return response.text.strip()


def enhance_description(title: str, company: str, description: str) -> str:
    prompt = f"""You are a senior technical recruiter.
Rewrite the following job description for the role "{title}" at "{company}" \
into a clear, engaging, and professional format.

Rules:
- Keep it concise (3-5 paragraphs)
- Use plain text only, no markdown, no bullet symbols
- Preserve the original intent but improve clarity and tone

Original description:
{description}

Return only the improved description text, nothing else."""
    return _generate(prompt)


def generate_requirements(title: str, company: str, description: str) -> str:
    prompt = f"""You are a senior technical recruiter.
Based on the job title "{title}" at "{company}" and the description below, \
generate a professional list of job requirements.

Rules:
- Include: technical skills, experience, soft skills, and nice-to-haves
- Format as a plain numbered list: 1. ... 2. ... 3. ...
- No markdown symbols, plain text only

Job description:
{description}

Return only the requirements list, nothing else."""
    return _generate(prompt)


def enhance_requirements(title: str, requirements: str) -> str:
    prompt = f"""You are a senior technical recruiter.
Improve and polish the following job requirements for the role "{title}".

Rules:
- Make them clear, professional, and well-structured
- Format as a plain numbered list: 1. ... 2. ... 3. ...
- No markdown symbols, plain text only
- Do not invent requirements not implied by the originals

Original requirements:
{requirements}

Return only the improved requirements list, nothing else."""
    return _generate(prompt)