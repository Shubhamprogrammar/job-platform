from datetime import date

from openai.lib._parsing._responses import type_to_text_format_param
from pydantic import ValidationError

from app.config import settings
from app.schemas import JobResult, JobSearchResult, ResumeProfile
from app.services.llm import get_client

SYSTEM_PROMPT = """You are a job search assistant with web search.
Rules:
- You MUST use web search to find real, currently open job postings. Never invent jobs.
- Prefer postings from the last 30 days on job boards (LinkedIn, Indeed, Naukri, Glassdoor, Wellfound) or company career pages.
- apply_url must be a URL you actually found in the search results, pointing to that specific posting.
- Skip postings that are closed, expired, or far outside the candidate's experience level.
- Do not return the same job twice.
- match_score: 0-100, based on skill overlap, experience fit and location fit.
- Keep each description under 40 words."""

MAX_OUTPUT_TOKENS = 16_000


def build_query(profile: ResumeProfile, location: str | None) -> str:
    """Human-readable search query built from skills, experience and location."""
    titles = ", ".join(profile.job_titles[:3]) or "Software Engineer"
    skills = ", ".join(profile.skills[:8])
    where = location or (profile.locations[0] if profile.locations else "Remote")
    return f"{titles} | {profile.total_experience_years:g} years experience | skills: {skills} | location: {where}"


def search_jobs(profile: ResumeProfile, location: str | None, max_jobs: int) -> tuple[str, list[JobResult]]:
    query = build_query(profile, location)
    where = location or ", ".join(profile.locations) or "Remote"
    user_prompt = f"""Today is {date.today().isoformat()}.
Find up to {max_jobs} open job postings for this candidate.

Target roles: {", ".join(profile.job_titles) or "based on skills"}
Experience: {profile.total_experience_years:g} years ({profile.seniority})
Key skills: {", ".join(profile.skills[:15])}
Location: {where} (remote roles open to this location are also fine)

Search query to start with: {query}"""

    try:
        result = _run_search(user_prompt)
    except TruncatedOutputError:
        # Too many jobs to fit in one reply — retry once asking for half as many.
        fewer = max(1, max_jobs // 2)
        result = _run_search(user_prompt.replace(f"Find up to {max_jobs} ", f"Find up to {fewer} ", 1))

    jobs = [j for j in result.jobs if j.apply_url.startswith(("http://", "https://"))]
    return query, jobs[:max_jobs]


class TruncatedOutputError(RuntimeError):
    pass


def _run_search(user_prompt: str) -> JobSearchResult:
    # create() + manual parsing (instead of parse()) so a cut-off reply can be detected and retried
    # rather than surfacing as a JSON parse crash.
    response = get_client().responses.create(
        model=settings.openai_search_model,
        tools=[{"type": "web_search"}],
        input=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        text={"format": type_to_text_format_param(JobSearchResult)},
        max_output_tokens=MAX_OUTPUT_TOKENS,
    )
    if response.status == "incomplete":
        reason = response.incomplete_details.reason if response.incomplete_details else "unknown"
        raise TruncatedOutputError(f"OpenAI reply was cut off ({reason}).")
    try:
        return JobSearchResult.model_validate_json(response.output_text)
    except ValidationError as e:
        raise TruncatedOutputError(f"OpenAI returned invalid job JSON: {e.errors()[0]['msg']}") from e
