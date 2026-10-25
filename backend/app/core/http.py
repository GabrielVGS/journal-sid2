from typing import Any

import httpx

from app.config import get_settings
from app.core.errors import SourceUnavailableError
from app.schemas import Source

_client: httpx.AsyncClient | None = None


# Um único cliente HTTP reaproveita conexões entre as requisições.
def get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        settings = get_settings()
        _client = httpx.AsyncClient(
            timeout=settings.http_timeout,
            headers={"User-Agent": settings.user_agent},
            follow_redirects=True,
        )
    return _client


async def close_client() -> None:
    if _client is not None:
        await _client.aclose()


# Qualquer falha de rede ou HTTP vira SourceUnavailableError com o nome da fonte.
async def get_json(
    source: Source,
    url: str,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> Any:
    try:
        response = await get_client().get(url, params=params, headers=headers)
        response.raise_for_status()
        return response.json()
    except httpx.TimeoutException:
        raise SourceUnavailableError(source, "timeout") from None
    except httpx.HTTPStatusError as exc:
        raise SourceUnavailableError(source, f"HTTP {exc.response.status_code}") from None
    except (httpx.HTTPError, ValueError) as exc:
        raise SourceUnavailableError(source, f"{type(exc).__name__}: {exc}") from None
