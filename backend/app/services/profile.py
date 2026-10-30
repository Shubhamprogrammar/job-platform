from app.config import settings
from app.schemas import ResumeProfile
from app.services.llm import get_client

SYSTEM_PROMPT = """You extract structured data from resumes.
- Only use information present in the resume; use null when something is missing.
- total_experience_years: sum of professional work periods (exclude education), rounded to one decimal.
- skills: deduplicated, canonical names (e.g. "JavaScript", not "JS"), most important first.
- job_titles: 2-5 role titles this candidate should search for."""

MAX_RESUME_CHARS = 30_000


def extract_profile(resume_text: str) -> ResumeProfile:
    response = get_client().responses.parse(
        model=settings.openai_model,
        input=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": resume_text[:MAX_RESUME_CHARS]},
        ],
        text_format=ResumeProfile,
    )
    if response.output_parsed is None:
        raise RuntimeError("OpenAI did not return a profile for this resume.")
    return response.output_parsed
