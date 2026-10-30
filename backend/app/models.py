from dataclasses import asdict, dataclass, field, fields
from datetime import UTC, datetime
from typing import Self


def _now() -> datetime:
    return datetime.now(UTC)


class _Document:
    """Maps between a dataclass (`id`) and a MongoDB document (`_id`)."""

    @classmethod
    def from_doc(cls, doc: dict) -> Self:
        names = {f.name for f in fields(cls)}
        return cls(id=doc["_id"], **{k: v for k, v in doc.items() if k in names and k != "id"})

    def to_doc(self) -> dict:
        doc = asdict(self)
        doc["_id"] = doc.pop("id")
        return doc


@dataclass
class Resume(_Document):
    """Collection `resumes`."""

    id: int
    file_name: str
    raw_text: str
    profile_json: dict
    created_at: datetime = field(default_factory=_now)


@dataclass
class Job(_Document):
    """Collection `jobs`."""

    id: int
    # sha256 of normalized title|company|location — the DB-level duplicate guard (unique index)
    fingerprint: str
    # sha256 of the normalized apply URL
    url_hash: str | None
    company_norm: str

    title: str
    company: str
    location: str | None = None
    employment_type: str | None = None
    experience_required: str | None = None
    salary: str | None = None
    description: str | None = None
    apply_url: str | None = None
    source: str | None = None
    posted_date: str | None = None
    created_at: datetime = field(default_factory=_now)


@dataclass
class ResumeJob:
    """Collection `resume_jobs`: which jobs were found for which resume, with that resume's match score."""

    resume_id: int
    job_id: int
    match_score: int | None = None
    matched_skills: list | None = None
    created_at: datetime = field(default_factory=_now)

    @classmethod
    def from_doc(cls, doc: dict) -> Self:
        names = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in doc.items() if k in names})
