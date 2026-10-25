import asyncio
from typing import Any

from app.core.cache import DAY, cached
from app.core.errors import SourceUnavailableError
from app.core.http import get_json
from app.schemas import Indicator, SeriesPoint

BASE_URL = "https://api.worldbank.org/v2/country/BR/indicator"
# Distância máxima entre o ano pedido e o ano com dado disponível.
WINDOW_YEARS = 3

INDICATORS: dict[str, tuple[str, str]] = {
    "SP.POP.TOTL": ("População", "habitantes"),
    "SP.DYN.LE00.IN": ("Expectativa de vida", "anos"),
    "NY.GDP.PCAP.CD": ("PIB per capita", "US$"),
    "SP.URB.TOTL.IN.ZS": ("População urbana", "%"),
    "SP.DYN.TFRT.IN": ("Filhos por mulher", "filhos"),
    "FP.CPI.TOTL.ZG": ("Inflação anual", "%"),
    "IT.NET.USER.ZS": ("Usuários de internet", "% da população"),
}

# Câmbio oficial anual (moeda local por dólar), usado antes de 2014.
EXCHANGE_RATE_CODE = "PA.NUS.FCRF"


@cached("worldbank", ttl=30 * DAY)
async def fetch_series_raw(code: str) -> list[dict[str, Any]]:
    body = await get_json(
        "worldbank", f"{BASE_URL}/{code}", params={"format": "json", "per_page": 100}
    )
    # A resposta é [metadados, dados]; erros chegam com HTTP 200 e sem a lista.
    if not isinstance(body, list) or len(body) < 2 or not isinstance(body[1], list):
        raise SourceUnavailableError("worldbank", f"unexpected answer for {code}")
    rows: list[dict[str, Any]] = body[1]
    return rows


def parse_series(rows: list[dict[str, Any]]) -> dict[int, float]:
    return {int(row["date"]): float(row["value"]) for row in rows if row.get("value") is not None}


async def fetch_series(code: str) -> dict[int, float]:
    return parse_series(await fetch_series_raw(code))


# Ano mais próximo com dado, dentro da janela.
def closest_year(series: dict[int, float], year: int, window: int = WINDOW_YEARS) -> int | None:
    candidates = [y for y in series if abs(y - year) <= window]
    return min(candidates, key=lambda y: (abs(y - year), y)) if candidates else None


def build_indicator(code: str, series: dict[int, float], year: int) -> Indicator | None:
    then_year = closest_year(series, year)
    if then_year is None:
        return None
    now_year = max(series)
    name, unit = INDICATORS[code]
    return Indicator(
        code=code,
        name=name,
        unit=unit,
        then_year=then_year,
        then_value=series[then_year],
        now_year=now_year,
        now_value=series[now_year],
        series=[SeriesPoint(year=y, value=series[y]) for y in sorted(series)],
    )


async def get_indicators(year: int) -> list[Indicator]:
    results = await asyncio.gather(
        *(fetch_series(code) for code in INDICATORS), return_exceptions=True
    )
    if all(isinstance(result, BaseException) for result in results):
        raise SourceUnavailableError("worldbank", "all indicator requests failed")
    indicators = []
    for code, result in zip(INDICATORS, results, strict=True):
        if isinstance(result, BaseException):
            continue
        indicator = build_indicator(code, result, year)
        if indicator is not None:
            indicators.append(indicator)
    return indicators
