"""Duplicate detection for found jobs.

Two layers:
1. Exact: normalized title|company|location fingerprint, or the same apply URL, already in MongoDB.
2. LLM: for remaining jobs whose company already has jobs in MongoDB, OpenAI decides whether
   a candidate is the same posting worded differently ("Sr. Python Dev" vs "Senior Python Developer").
"""

import hashlib
import json
import re
from urllib.parse import parse_qsl, urlencode, urlsplit

from pymongo.database import Database

from app.config import settings
from app.models import Job
from app.schemas import DuplicateCheck, JobResult
from app.services.llm import get_client

_COMPANY_SUFFIXES = re.compile(
    r"\b(inc|incorporated|llc|ltd|limited|pvt|private|corp|corporation|co|gmbh|plc|technologies|tech)\b\.?"
)
_TITLE_ABBREVIATIONS = {"sr": "senior", "jr": "junior", "dev": "developer", "engg": "engineer", "mgr": "manager"}
_TRACKING_PARAMS = re.compile(r"^(utm_|ref|refid|trk|src|source|from|gclid|fbclid)", re.I)
MAX_EXISTING_FOR_LLM = 60


def _clean(text: str | None) -> str:
    text = (text or "").lower()
    text = re.sub(r"[^a-z0-9 ]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def normalize_title(title: str) -> str:
    return " ".join(_TITLE_ABBREVIATIONS.get(w, w) for w in _clean(title).split())


def normalize_company(company: str) -> str:
    return re.sub(r"\s+", " ", _COMPANY_SUFFIXES.sub(" ", _clean(company))).strip()


def fingerprint(job: JobResult) -> str:
    key = f"{normalize_title(job.title)}|{normalize_company(job.company)}|{_clean(job.location)}"
    return hashlib.sha256(key.encode()).hexdigest()


def url_hash(url: str | None) -> str | None:
    if not url:
        return None
    parts = urlsplit(url.strip())
    host = parts.netloc.lower().removeprefix("www.")
    query = urlencode(sorted((k, v) for k, v in parse_qsl(parts.query) if not _TRACKING_PARAMS.match(k)))
    normalized = f"{host}{parts.path.rstrip('/')}?{query}"
    return hashlib.sha256(normalized.encode()).hexdigest()


def find_duplicates(db: Database, candidates: list[JobResult]) -> list[tuple[JobResult, Job | None]]:
    """Return each unique candidate paired with the existing DB job it duplicates (or None if new)."""
    # Drop duplicates within this batch first.
    unique: dict[str, JobResult] = {}
    for job in candidates:
        unique.setdefault(fingerprint(job), job)
    batch = list(unique.values())

    # Layer 1: exact fingerprint / URL match.
    fps = [fingerprint(j) for j in batch]
    urls = [h for h in (url_hash(j.apply_url) for j in batch) if h]
    existing = [
        Job.from_doc(d)
        for d in db.jobs.find({"$or": [{"fingerprint": {"$in": fps}}, {"url_hash": {"$in": urls}}]})
    ]
    by_fp = {j.fingerprint: j for j in existing}
    by_url = {j.url_hash: j for j in existing if j.url_hash}

    results: list[tuple[JobResult, Job | None]] = []
    unresolved: list[int] = []
    for job, fp in zip(batch, fps):
        match = by_fp.get(fp) or by_url.get(url_hash(job.apply_url))
        results.append((job, match))
        if match is None:
            unresolved.append(len(results) - 1)

    # Layer 2: LLM check against existing jobs at the same companies.
    if unresolved:
        companies = {normalize_company(results[i][0].company) for i in unresolved}
        same_company = [
            Job.from_doc(d)
            for d in db.jobs.find({"company_norm": {"$in": list(companies)}})
            .sort("created_at", -1)
            .limit(MAX_EXISTING_FOR_LLM)
        ]
        if same_company:
            for idx, job in _llm_duplicates(results, unresolved, same_company).items():
                results[idx] = (results[idx][0], job)

    return results


def _llm_duplicates(
    results: list[tuple[JobResult, Job | None]], unresolved: list[int], existing: list[Job]
) -> dict[int, Job]:
    candidates = [
        {"candidate_index": i, "title": results[i][0].title, "company": results[i][0].company,
         "location": results[i][0].location, "url": results[i][0].apply_url}
        for i in unresolved
    ]
    known = [
        {"existing_job_id": j.id, "title": j.title, "company": j.company, "location": j.location, "url": j.apply_url}
        for j in existing
    ]
    prompt = (
        "Decide which NEW job postings are the same posting as an EXISTING one "
        "(same company, same role, same location, possibly worded differently). "
        "Different seniority, team or city means NOT a duplicate. Only report confident matches.\n\n"
        f"NEW:\n{json.dumps(candidates, indent=1)}\n\nEXISTING:\n{json.dumps(known, indent=1)}"
    )
    response = get_client().responses.parse(
        model=settings.openai_model, input=prompt, text_format=DuplicateCheck
    )
    if response.output_parsed is None:
        return {}

    valid_idx = set(unresolved)
    jobs_by_id = {j.id: j for j in existing}
    return {
        d.candidate_index: jobs_by_id[d.existing_job_id]
        for d in response.output_parsed.duplicates
        if d.candidate_index in valid_idx and d.existing_job_id in jobs_by_id
    }
