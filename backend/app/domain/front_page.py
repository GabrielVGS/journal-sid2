import asyncio
import logging
from datetime import date, datetime

from psycopg.types.json import Jsonb

from app.core import dates
from app.core.db import get_pool
from app.core.errors import SourceUnavailableError
from app.domain.editorial import build_editorial
from app.schemas import FrontPage, Source, SourceStatus
from app.services import ipeadata, wikipedia, worldbank

# Desativado: Lua e céu noturno
# from app.services import moon, sky
from app.services.exchange import get_exchange

logger = logging.getLogger(__name__)

SOURCES: list[Source] = ["wikipedia", "worldbank", "alphavantage", "ipeadata", "llm"]


async def load(day: date) -> FrontPage | None:
    async with get_pool().connection() as connection:
        cursor = await connection.execute("SELECT page FROM front_pages WHERE date = %s", (day,))
        row = await cursor.fetchone()
    return FrontPage.model_validate(row[0]) if row else None


async def save(page: FrontPage) -> None:
    async with get_pool().connection() as connection:
        await connection.execute(
            "INSERT INTO front_pages (date, page, created_at) VALUES (%s, %s, %s) "
            "ON CONFLICT (date) DO UPDATE "
            "SET page = EXCLUDED.page, created_at = EXCLUDED.created_at",
            (page.date, Jsonb(page.model_dump(mode="json")), page.generated_at),
        )


def _failure(source: Source, error: BaseException) -> SourceUnavailableError:
    if isinstance(error, SourceUnavailableError):
        return error
    logger.exception("Unexpected error in %s", source, exc_info=error)
    return SourceUnavailableError(source, f"internal error: {type(error).__name__}")


# Monta a capa completa consultando todas as fontes em paralelo.
async def build_front_page(day: date) -> FrontPage:
    stored = await load(day)
    if stored is not None:
        for status in stored.sources:
            status.cached = True
        return stored

    (
        events,
        # sky_result,  (desativado)
        indicators_result,
        exchange_result,
        money_result,
        people,
    ) = await asyncio.gather(
        wikipedia.get_events(day),
        # sky.get_sky(day),  (desativado)
        worldbank.get_indicators(day.year),
        get_exchange(day),
        ipeadata.get_money(day),
        asyncio.gather(
            wikipedia.get_births(day), wikipedia.get_deaths(day), return_exceptions=True
        ),
        return_exceptions=True,
    )
    births, deaths = ([], []) if isinstance(people, BaseException) else people
    # Sem a Wikipedia não há jornal; as demais fontes podem falhar.
    if isinstance(events, BaseException):
        raise _failure("wikipedia", events)

    failures: dict[Source, SourceUnavailableError] = {}
    # Desativado: céu noturno
    # night_sky = None
    # if isinstance(sky_result, BaseException):
    #     failures["nasa"] = _failure("nasa", sky_result)
    # else:
    #     night_sky = sky_result
    indicators = []
    if isinstance(indicators_result, BaseException):
        failures["worldbank"] = _failure("worldbank", indicators_result)
    else:
        indicators = indicators_result
    if isinstance(exchange_result, BaseException):
        failures["alphavantage"] = _failure("alphavantage", exchange_result)
        exchange = None
    else:
        exchange, exchange_errors = exchange_result
        for error in exchange_errors:
            failures.setdefault(error.source, error)

    money = None
    if isinstance(money_result, BaseException):
        failures["ipeadata"] = _failure("ipeadata", money_result)
    else:
        money = money_result

    editorial, llm_error = await build_editorial(day, events, indicators, exchange)
    if llm_error is not None:
        failures["llm"] = llm_error

    page = FrontPage(
        date=day,
        issue_number=dates.issue_number(day),
        events=events,
        indicators=indicators,
        exchange=exchange,
        editorial=editorial,
        births=[] if isinstance(births, BaseException) else births,
        deaths=[] if isinstance(deaths, BaseException) else deaths,
        money=money,
        # Desativado: Lua e céu noturno
        # moon=moon.moon_on(day),
        # sky=night_sky,
        sources=[
            SourceStatus(
                source=source,
                ok=source not in failures,
                message=f"Fonte indisponível ({failures[source].reason})"
                if source in failures
                else None,
            )
            for source in SOURCES
        ],
        generated_at=datetime.now(dates.TIMEZONE),
    )
    # Só salva a capa se todas as fontes responderam.
    if not failures:
        await save(page)
    return page
