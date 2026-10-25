from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parents[2]


# Configurações lidas de variáveis de ambiente ou do arquivo .env.
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT_DIR / ".env", extra="ignore")

    alphavantage_api_key: str = ""
    av_daily_cap: int = 20

    llm_api_key: str = ""
    llm_base_url: str = "https://openrouter.ai/api/v1"
    llm_model: str = "anthropic/claude-haiku-5.5"
    llm_fallback_models: Annotated[list[str], NoDecode] = [
        "google/gemini-2.5-flash",
        "openai/gpt-4o-mini",
    ]

    # A Wikimedia exige um User-Agent com contato; sem ele responde 403.
    user_agent: str = (
        "JornalDoDia/0.1 (https://github.com/GabrielVGS/journal-sid2; academic project)"
    )

    site_password: str = ""

    database_url: str = ""
    http_timeout: float = 15.0

    @field_validator("llm_fallback_models", mode="before")
    @classmethod
    def _split_models(cls, value: object) -> object:
        if isinstance(value, str):
            return [model.strip() for model in value.split(",") if model.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
