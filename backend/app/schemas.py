from datetime import datetime

from pydantic import BaseModel, Field

# ---------- Schemas OpenAI fills in (Structured Outputs: no defaults allowed) ----------


class ExperienceItem(BaseModel):
    company: str
    role: str
    start: str | None = Field(description="Start date as written, e.g. 'Jan 2021'")
    end: str | None = Field(description="End date, or 'Present'")
    summary: str = Field(description="One or two sentence summary of the work")


class ResumeProfile(BaseModel):
    name: str | None
    email: str | None
    total_experience_years: float = Field(description="Total professional experience in years")
    seniority: str = Field(description="One of: intern, entry, junior, mid, senior, lead, principal")
    job_titles: list[str] = Field(description="Roles this person is suited for, most relevant first")
    skills: list[str] = Field(description="Technical and professional skills, most important first")
    experience: list[ExperienceItem]
    locations: list[str] = Field(description="Current / preferred locations found in the resume")


class JobResult(BaseModel):
    title: str
    company: str
    location: str | None
    employment_type: str | None = Field(description="Full-time, Contract, Internship, ...")
    experience_required: str | None = Field(description="e.g. '2-4 years'")
    salary: str | None
    description: str = Field(description="2-3 sentence summary of the role")
    apply_url: str = Field(description="Direct URL of the posting, taken from the search results")
    source: str = Field(description="Site the posting was found on, e.g. LinkedIn, Naukri, company site")
    posted_date: str | None
    match_score: int = Field(description="0-100 fit between the candidate and this job")
    matched_skills: list[str] = Field(description="Candidate skills this job asks for")


class JobSearchResult(BaseModel):
    jobs: list[JobResult]


class DuplicateMatch(BaseModel):
    candidate_index: int
    existing_job_id: int


class DuplicateCheck(BaseModel):
    duplicates: list[DuplicateMatch]


# ---------- API request / response schemas ----------


class ResumeOut(BaseModel):
    id: int
    file_name: str
    profile: ResumeProfile
    created_at: datetime


class SearchRequest(BaseModel):
    location: str | None = Field(default=None, description="Overrides the location from the resume")
    max_jobs: int = Field(default=15, ge=1, le=30)


class JobOut(BaseModel):
    id: int
    title: str
    company: str
    location: str | None
    employment_type: str | None
    experience_required: str | None
    salary: str | None
    description: str | None
    apply_url: str | None
    source: str | None
    posted_date: str | None
    match_score: int | None = None
    matched_skills: list[str] = []
    is_new: bool = False
    created_at: datetime


class SearchResponse(BaseModel):
    query: str
    new_jobs: int
    duplicates_rejected: int
    jobs: list[JobOut]
