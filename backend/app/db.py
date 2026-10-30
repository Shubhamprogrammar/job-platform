from pymongo import ASCENDING, DESCENDING, MongoClient, ReturnDocument
from pymongo.database import Database

from app.config import settings

client = MongoClient(settings.mongodb_url, tz_aware=True)
db: Database = client.get_default_database(default="job_platform")


def get_db() -> Database:
    return db


def next_id(db: Database, collection: str) -> int:
    """Auto-increment integer ids (like MySQL AUTO_INCREMENT) so the API keeps numeric ids."""
    counter = db.counters.find_one_and_update(
        {"_id": collection}, {"$inc": {"seq": 1}}, upsert=True, return_document=ReturnDocument.AFTER
    )
    return counter["seq"]


def create_indexes(db: Database) -> None:
    # fingerprint is UNIQUE — the DB-level duplicate guard
    db.jobs.create_index("fingerprint", unique=True)
    db.jobs.create_index("url_hash")
    db.jobs.create_index("company_norm")
    db.jobs.create_index([("created_at", DESCENDING)])
    db.resume_jobs.create_index([("resume_id", ASCENDING), ("job_id", ASCENDING)], unique=True)
    db.resume_jobs.create_index([("resume_id", ASCENDING), ("match_score", DESCENDING)])
