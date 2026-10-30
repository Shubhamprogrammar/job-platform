from functools import lru_cache

from openai import OpenAI

from app.config import settings


@lru_cache
def get_client() -> OpenAI:
    return OpenAI(api_key=settings.openai_api_key or None)
