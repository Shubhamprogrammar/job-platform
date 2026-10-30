from contextlib import asynccontextmanager

import openai
from fastapi import Depends, FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError
from pymongo.database import Database

from app import models
from app.config import settings
from app.db import create_indexes, db as mongo_db, get_db, next_id
from app.schemas import JobOut, JobResult, ResumeOut, ResumeProfile, SearchRequest, SearchResponse
from app.services import dedup
from app.services.parser import SUPPORTED_EXTENSIONS, extract_text
from app.services.profile import extract_profile
from app.services.search import search_jobs


@asynccontextmanager
async def lifespan(_: FastAPI):
    create_indexes(mongo_db)
    yield


app = FastAPI(title="Job Platform API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _resume_out(resume: models.Resume) -> ResumeOut:
    return ResumeOut(
        id=resume.id,
        file_name=resume.file_name,
        profile=ResumeProfile.model_validate(resume.profile_json),
        created_at=resume.created_at,
    )


def _job_out(job: models.Job, link: models.ResumeJob, new_ids: set[int] = frozenset()) -> JobOut:
    return JobOut(
        id=job.id,
        title=job.title,
        company=job.company,
        location=job.location,
        employment_type=job.employment_type,
        experience_required=job.experience_required,
        salary=job.salary,
        description=job.description,
        apply_url=job.apply_url,
        source=job.source,
        posted_date=job.posted_date,
        match_score=link.match_score,
        matched_skills=link.matched_skills or [],
        is_new=job.id in new_ids,
        created_at=job.created_at,
    )


def _get_resume(db: Database, resume_id: int) -> models.Resume:
    doc = db.resumes.find_one({"_id": resume_id})
    if doc is None:
        raise HTTPException(404, "Resume not found")
    return models.Resume.from_doc(doc)


def _resume_jobs(db: Database, resume_id: int, new_ids: set[int] = frozenset()) -> list[JobOut]:
    links = [models.ResumeJob.from_doc(d) for d in db.resume_jobs.find({"resume_id": resume_id}).sort("match_score", -1)]
    jobs = {d["_id"]: models.Job.from_doc(d) for d in db.jobs.find({"_id": {"$in": [l.job_id for l in links]}})}
    return [_job_out(jobs[link.job_id], link, new_ids) for link in links if link.job_id in jobs]


def _new_job(db: Database, result: JobResult) -> models.Job:
    return models.Job(
        id=next_id(db, "jobs"),
        fingerprint=dedup.fingerprint(result),
        url_hash=dedup.url_hash(result.apply_url),
        company_norm=dedup.normalize_company(result.company)[:255],
        title=result.title[:255],
        company=result.company[:255],
        location=result.location[:255] if result.location else None,
        employment_type=result.employment_type,
        experience_required=result.experience_required,
        salary=result.salary,
        description=result.description,
        apply_url=result.apply_url[:1024],
        source=result.source[:255],
        posted_date=result.posted_date,
    )


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/resumes", response_model=ResumeOut)
def upload_resume(file: UploadFile = File(...), db: Database = Depends(get_db)):
    data = file.file.read()
    if len(data) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(413, f"File is larger than {settings.max_upload_mb} MB")
    file_name = file.filename or "resume"

    try:
        text = extract_text(file_name, data)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e

    try:
        profile = extract_profile(text)
    except (openai.OpenAIError, RuntimeError, ValidationError) as e:
        raise HTTPException(502, f"Resume parsing failed: {e}") from e

    resume = models.Resume(
        id=next_id(db, "resumes"), file_name=file_name, raw_text=text, profile_json=profile.model_dump()
    )
    db.resumes.insert_one(resume.to_doc())
    return _resume_out(resume)


@app.get("/api/resumes/{resume_id}", response_model=ResumeOut)
def get_resume(resume_id: int, db: Database = Depends(get_db)):
    return _resume_out(_get_resume(db, resume_id))


@app.post("/api/resumes/{resume_id}/search", response_model=SearchResponse)
def search_for_resume(resume_id: int, body: SearchRequest, db: Database = Depends(get_db)):
    resume = _get_resume(db, resume_id)
    profile = ResumeProfile.model_validate(resume.profile_json)

    try:
        query, candidates = search_jobs(profile, body.location, body.max_jobs)
        classified = dedup.find_duplicates(db, candidates)
    except (openai.OpenAIError, RuntimeError, ValidationError) as e:
        raise HTTPException(502, f"Job search failed: {e}") from e

    new_ids: set[int] = set()
    rejected = 0
    for result, existing in classified:
        if existing is not None:
            job = existing
            rejected += 1
        else:
            job = _new_job(db, result)
            db.jobs.insert_one(job.to_doc())
            new_ids.add(job.id)
        # Link the job to this resume either way, so known jobs still show in this resume's table.
        link = models.ResumeJob(
            resume_id=resume.id,
            job_id=job.id,
            match_score=max(0, min(100, result.match_score)),
            matched_skills=result.matched_skills,
        )
        db.resume_jobs.update_one(
            {"resume_id": link.resume_id, "job_id": link.job_id},
            {
                "$set": {"match_score": link.match_score, "matched_skills": link.matched_skills},
                "$setOnInsert": {"created_at": link.created_at},
            },
            upsert=True,
        )

    return SearchResponse(
        query=query,
        new_jobs=len(new_ids),
        duplicates_rejected=rejected,
        jobs=_resume_jobs(db, resume.id, new_ids),
    )


@app.get("/api/resumes/{resume_id}/jobs", response_model=list[JobOut])
def list_resume_jobs(resume_id: int, db: Database = Depends(get_db)):
    _get_resume(db, resume_id)
    return _resume_jobs(db, resume_id)


@app.get("/api/jobs", response_model=list[JobOut])
def list_jobs(
    limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0), db: Database = Depends(get_db)
):
    jobs = [models.Job.from_doc(d) for d in db.jobs.find().sort("created_at", -1).skip(offset).limit(limit)]
    return [
        JobOut(**{c: getattr(j, c) for c in JobOut.model_fields if hasattr(j, c) and c != "matched_skills"})
        for j in jobs
    ]
