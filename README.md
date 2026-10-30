# Job Platform

Upload a resume → OpenAI extracts skills, experience and location → OpenAI web search finds matching jobs →
duplicates are rejected → new jobs are saved to MongoDB and shown in a table.

```
frontend/ (Next.js)  ──►  backend/ (FastAPI)  ──►  OpenAI (Structured Outputs + web_search)
                                   │
                                   └──►  MongoDB (resumes, jobs, resume_jobs)
```

## Run

```bash
# 1. MongoDB
docker compose up -d

# 2. Backend
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env          # set OPENAI_API_KEY
.venv/bin/uvicorn app.main:app --reload --port 8000

# 3. Frontend
cd frontend
npm install
cp .env.local.example .env.local
npm run dev                   # http://localhost:3000
```

Indexes are created automatically on backend startup. API docs: http://localhost:8000/docs

## API

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/resumes` | Upload PDF/DOCX/TXT → extracted profile JSON |
| GET | `/api/resumes/{id}` | Get a stored resume profile |
| POST | `/api/resumes/{id}/search` | `{ "location": "Pune", "max_jobs": 15 }` → web search, dedup, save, return jobs |
| GET | `/api/resumes/{id}/jobs` | All jobs found for a resume |
| GET | `/api/jobs` | All stored jobs (paginated) |

## Duplicate rejection

`backend/app/services/dedup.py`

1. **Exact**: a fingerprint of the normalized `title | company | location`
   (e.g. "Sr. Python Dev @ Acme Pvt Ltd" == "Senior Python Developer @ Acme"), or the same apply URL
   with tracking parameters removed. `jobs.fingerprint` has a unique index in MongoDB.
2. **LLM**: remaining jobs from companies that already have jobs in the DB are sent to OpenAI along with
   those existing jobs, and OpenAI flags the ones that are the same posting.

Rejected jobs are not inserted again, but they are still linked to the current resume, so they show in its table.
