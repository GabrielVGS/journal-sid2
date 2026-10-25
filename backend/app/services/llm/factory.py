from app.config import get_settings
from app.services.llm.base import LLMClient
from app.services.llm.openai_compat import OpenAICompatClient

_client: LLMClient | None = None


# Modelo principal seguido dos modelos de reserva.
def get_llm_client() -> LLMClient:
    global _client
    if _client is None:
        settings = get_settings()
        _client = OpenAICompatClient(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
            models=[settings.llm_model, *settings.llm_fallback_models],
        )
    return _client


def set_llm_client(client: LLMClient | None) -> None:
    global _client
    _client = client
