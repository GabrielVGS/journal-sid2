import asyncio
import math
from datetime import date
from typing import Any

from app.core import dates
from app.core.cache import DAY, cached
from app.core.errors import SourceUnavailableError
from app.core.http import get_json
from app.schemas import Money
from app.services.currencies import currency_on

BASE_URL = "https://www.ipeadata.gov.br/api/odata4/ValoresSerie(SERCODIGO='{code}')"
# Salário mínimo nominal (em reais) e corrigido pela inflação.
NOMINAL_CODE = "MTE12_SALMIN12"
REAL_CODE = "GAC12_SALMINRE12"
WINDOW_MONTHS = 12
FIRST_MONTH = "1940-07"


@cached("ipeadata", ttl=30 * DAY)
async def fetch_series_raw(code: str) -> list[dict[str, Any]]:
    body = await get_json("ipeadata", BASE_URL.format(code=code))
    if not isinstance(body, dict) or not isinstance(body.get("value"), list):
        raise SourceUnavailableError("ipeadata", f"unexpected answer for {code}")
    rows: list[dict[str, Any]] = body["value"]
    return rows


def parse_series(rows: list[dict[str, Any]]) -> dict[str, float]:
    return {
        str(row["VALDATA"])[:7]: float(row["VALVALOR"])
        for row in rows
        if row.get("VALVALOR") is not None and row.get("VALDATA")
    }


async def fetch_series(code: str) -> dict[str, float]:
    return parse_series(await fetch_series_raw(code))


def month_at_or_before(series: dict[str, float], month: str) -> str | None:
    year, number = int(month[:4]), int(month[5:7])
    for back in range(WINDOW_MONTHS + 1):
        total = year * 12 + number - 1 - back
        candidate = f"{total // 12:04d}-{total % 12 + 1:02d}"
        if candidate in series:
            return candidate
    return None


def round_amount(value: float) -> float:
    return float(10 ** math.floor(math.log10(value)))


def build_money(day: date, nominal: dict[str, float], real: dict[str, float]) -> Money:
    currency = currency_on(day)
    money = Money(currency_symbol=currency.symbol)
    month = f"{day:%Y-%m}"
    if month < FIRST_MONTH:
        money.note = "O salário mínimo só foi criado em julho de 1940."
        return money
    if nominal:
        current = month_at_or_before(nominal, f"{dates.today():%Y-%m}")
        money.min_wage_now = nominal[current or max(nominal)]
    both = {key: value for key, value in nominal.items() if key in real}
    then = month_at_or_before(both, month) or month_at_or_before(nominal, month)
    if then is None:
        return money
    money.period = then
    # A série nominal vem em reais; converte para a moeda da época.
    money.min_wage_then = nominal[then] * currency.per_real
    if then in real and nominal[then] > 0:
        # Fator de inflação: quanto 1 real daquele mês vale hoje.
        correction = real[then] / nominal[then]
        money.today_period = max(real)
        money.min_wage_then_today = real[then]
        money.amount_then = round_amount(money.min_wage_then)
        money.amount_today = money.amount_then / currency.per_real * correction
        money.note = "Valores corrigidos pela inflação (INPC/ICV), segundo o Ipea."
    return money


async def get_money(day: date) -> Money:
    if f"{day:%Y-%m}" < FIRST_MONTH:
        return build_money(day, {}, {})
    nominal, real = await asyncio.gather(
        fetch_series(NOMINAL_CODE), fetch_series(REAL_CODE), return_exceptions=True
    )
    if isinstance(nominal, BaseException) and isinstance(real, BaseException):
        raise SourceUnavailableError("ipeadata", "no minimum wage series answered")
    return build_money(
        day,
        {} if isinstance(nominal, BaseException) else nominal,
        {} if isinstance(real, BaseException) else real,
    )
