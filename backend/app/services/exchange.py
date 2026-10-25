from datetime import date

from app.core.errors import SourceUnavailableError
from app.schemas import Exchange
from app.services import alphavantage, worldbank
from app.services.currencies import currency_on


async def _worldbank_rates(errors: list[SourceUnavailableError]) -> dict[int, float]:
    try:
        return await worldbank.fetch_series(worldbank.EXCHANGE_RATE_CODE)
    except SourceUnavailableError as exc:
        errors.append(exc)
        return {}


# Dólar mensal da Alpha Vantage quando existe; senão, média anual do World Bank.
async def get_exchange(day: date) -> tuple[Exchange, list[SourceUnavailableError]]:
    currency = currency_on(day)
    errors: list[SourceUnavailableError] = []
    try:
        monthly = await alphavantage.fetch_usd_brl_monthly()
    except SourceUnavailableError as exc:
        errors.append(exc)
        monthly = {}

    exchange = Exchange(currency=currency.to_schema())
    month = f"{day:%Y-%m}"
    yearly: dict[int, float] | None = None

    if month in monthly:
        exchange.usd_then = monthly[month]
        exchange.usd_then_period = month
        exchange.usd_then_source = "alphavantage"
        exchange.note = "Fechamento mensal do dólar comercial."
    else:
        yearly = await _worldbank_rates(errors)
        year = worldbank.closest_year(yearly, day.year)
        if year is not None:
            # O World Bank já converte tudo para reais; volta para a moeda da época.
            exchange.usd_then = yearly[year] * currency.per_real
            exchange.usd_then_period = str(year)
            exchange.usd_then_source = "worldbank"
            converted = "" if currency.per_real == 1 else ", convertida para a moeda da época"
            exchange.note = f"Média anual de {year} (Banco Mundial){converted}."
        elif day.year < 1960:
            exchange.note = "Não há cotação oficial do dólar anterior a 1960 em nossas fontes."

    if monthly:
        latest = max(monthly)
        exchange.usd_now, exchange.usd_now_period = monthly[latest], latest
    else:
        yearly = yearly if yearly is not None else await _worldbank_rates(errors)
        if yearly:
            latest_year = max(yearly)
            exchange.usd_now, exchange.usd_now_period = yearly[latest_year], str(latest_year)
    return exchange, errors
