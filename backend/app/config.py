from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openai_api_key: str = ""
    openai_model: str = "gpt-4.1-mini"
    openai_search_model: str = "gpt-4.1-mini"
    mongodb_url: str = "mongodb://localhost:27017/job_platform"
    cors_origins: list[str] = ["http://localhost:3000"]
    max_upload_mb: int = 5


settings = Settings()
