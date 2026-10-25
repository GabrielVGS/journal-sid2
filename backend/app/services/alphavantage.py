from typing import Any

from app.config import get_settings
from app.core import dates
from app.core.cache import DAY, cached
from app.core.db import get_pool
from app.core.errors import SourceUnavailableError
from app.core.http import get_json

URL = "https://www.alphavantage.co/query"
SERIES_KEY = "Time Series FX (Monthly)"
# Ao estourar a cota a API responde 200 com uma destas chaves no lugar dos dados.
ERROR_KEYS = ("Note", "Information", "Error Message")


async def calls_used_today() -> int:
    async with get_pool().connection() as connection:
        cursor = await connection.execute(
            "SELECT calls FROM av_quota WHERE day = %s", (dates.today(),)
        )
        row = await cursor.fetchone()
    return int(row[0]) if row else 0


async def calls_left_today() -> int:
    return max(get_settings().av_daily_cap - await calls_used_today(), 0)


# Reserva uma chamada da cota diária de forma atômica no banco.
async def _spend_one_call() -> None:
    cap = get_settings().av_daily_cap
    async with get_pool().connection() as connection:
        cursor = await connection.execute(
            "INSERT INTO av_quota (day, calls) VALUES (%s, 1) "
            "ON CONFLICT (day) DO UPDATE SET calls = av_quota.calls + 1 WHERE av_quota.calls < %s "
            "RETURNING calls",
            (dates.today(), cap),
        )
        counted = await cursor.fetchone()
    if cap <= 0 or counted is None:
        raise SourceUnavailableError("alphavantage", "daily cap reached")


# Uma chamada traz a série mensal inteira; fica em cache por 7 dias.
@cached("alphavantage:fx_monthly", ttl=7 * DAY)
async def fetch_usd_brl_monthly_raw() -> dict[str, Any]:
    settings = get_settings()
    if not settings.alphavantage_api_key:
        raise SourceUnavailableError("alphavantage", "missing API key")
    await _spend_one_call()
    params = {
        "function": "FX_MONTHLY",
        "from_symbol": "USD",
        "to_symbol": "BRL",
        "apikey": settings.alphavantage_api_key,
    }
    body = await get_json("alphavantage", URL, params=params)
    for key in ERROR_KEYS:
        if key in body:
            raise SourceUnavailableError("alphavantage", f"{key}: {str(body[key])[:120]}")
    if SERIES_KEY not in body:
        raise SourceUnavailableError("alphavantage", "unexpected answer")
    series: dict[str, Any] = body[SERIES_KEY]
    return series


async def fetch_usd_brl_monthly() -> dict[str, float]:
    raw = await fetch_usd_brl_monthly_raw()
    return {day[:7]: float(values["4. close"]) for day, values in raw.items()}
