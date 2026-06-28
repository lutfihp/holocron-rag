from functools import lru_cache
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False)

    database_url: str
    test_database_url: str
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_ttl_hours: int = 24
    cookie_name: str = "holocron_session"
    cookie_secure: bool = False
    cors_origins: Annotated[list[str], NoDecode] = Field(default_factory=list)
    groq_api_key: str = ""
    llm_primary_model: str = "llama-3.3-70b-versatile"
    llm_fallback_model: str = "llama-3.1-8b-instant"
    # Phase D: when truthy, FastAPI lifespan skips BGE + spaCy warming. Convenient
    # for uvicorn --reload dev loops and the pytest suite (tests use FakeEmbedding
    # and never need the real BGE model warmed).
    skip_warmup: bool = False
    # Phase D: when truthy, structlog uses ConsoleRenderer (human-readable, dev);
    # otherwise JSONRenderer (prod, eval, demo recording).
    log_pretty: bool = False

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_csv(cls, v: object) -> object:
        if isinstance(v, str):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
