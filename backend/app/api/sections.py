from typing import Annotated

from fastapi import APIRouter, Query, Request

from app.api.deps import ERROR_RESPONSES, ValidDate
from app.core import dates, limits
from app.core.errors import SourceUnavailableError
from app.domain import editorial as editorial_domain
from app.domain import front_page
from app.schemas import (
    ApiError,
    Birth,
    City,
    Editorial,
    EditorialRequest,
    Event,
    Exchange,
    Indicator,
    Money,
    Weather,
)
from app.services import ipeadata, weather, wikipedia, worldbank
from app.services.exchange import get_exchange

# Uma rota por seção da capa; cada uma usa a capa salva quando existe.
router = APIRouter(prefix="/api", tags=["sections"])


@router.get("/events", response_model=list[Event], responses=ERROR_RESPONSES)
async def get_events(date: ValidDate) -> list[Event]:
    stored = await front_page.load(date)
    return stored.events if stored else await wikipedia.get_events(date)


@router.get("/births", response_model=list[Birth], responses=ERROR_RESPONSES)
async def get_births(date: ValidDate) -> list[Birth]:
    stored = await front_page.load(date)
    if stored and stored.births:
        return stored.births
    return await wikipedia.get_births(date)


@router.get("/deaths", response_model=list[Birth], responses=ERROR_RESPONSES)
async def get_deaths(date: ValidDate) -> list[Birth]:
    stored = await front_page.load(date)
    if stored and stored.deaths:
        return stored.deaths
    return await wikipedia.get_deaths(date)


@router.get("/cities", response_model=list[City])
async def get_cities() -> list[City]:
    return weather.list_cities()


@router.get("/cities/search", response_model=list[City], responses=ERROR_RESPONSES)
async def search_cities(
    q: Annotated[str, Query(description="Part of the city name (2-60 letters).")],
) -> list[City]:
    return await weather.search_cities(q)


@router.get("/weather", response_model=Weather, responses=ERROR_RESPONSES)
async def get_weather(
    date: ValidDate,
    city: Annotated[
        str, Query(description="Slug from /api/cities or /api/cities/search.")
    ] = weather.DEFAULT_CITY,
) -> Weather:
    return await weather.get_weather(date, city)


@router.get("/indicators", response_model=list[Indicator], responses=ERROR_RESPONSES)
async def get_indicators(date: ValidDate) -> list[Indicator]:
    stored = await front_page.load(date)
    return stored.indicators if stored else await worldbank.get_indicators(date.year)


@router.get("/exchange", response_model=Exchange, responses=ERROR_RESPONSES)
async def get_exchange_section(date: ValidDate) -> Exchange:
    stored = await front_page.load(date)
    if stored and stored.exchange:
        return stored.exchange
    exchange, _ = await get_exchange(date)
    return exchange


@router.get("/money", response_model=Money, responses=ERROR_RESPONSES)
async def get_money(date: ValidDate) -> Money:
    stored = await front_page.load(date)
    if stored and stored.money:
        return stored.money
    return await ipeadata.get_money(date)


# Desativado: Lua e céu noturno
# @router.get("/moon", response_model=Moon, responses=ERROR_RESPONSES)
# async def get_moon(date: ValidDate) -> Moon:
#     return moon.moon_on(date)
#
#
# @router.get("/sky", response_model=Sky, responses=ERROR_RESPONSES)
# async def get_sky(date: ValidDate) -> Sky:
#     stored = await front_page.load(date)
#     if stored and stored.sky and stored.sky.guide:
#         return stored.sky
#     return await sky.get_sky(date)


@router.post(
    "/editorial",
    response_model=Editorial,
    responses={
        **ERROR_RESPONSES,
        429: {"model": ApiError, "description": "Too many new editorials."},
    },
)
# Recebe só a data: os fatos são montados no servidor, nunca vêm do cliente.
async def create_editorial(body: EditorialRequest, request: Request) -> Editorial:
    day = dates.validate(body.date)
    stored_page = await front_page.load(day)
    if stored_page is not None and stored_page.editorial is not None:
        return stored_page.editorial
    stored = await editorial_domain.load_stored(day)
    if stored is not None:
        return stored
    # Só conta no limite quando o editorial ainda não existe.
    limits.check_new_page(request)
    events = await wikipedia.get_events(day)
    try:
        indicators = await worldbank.get_indicators(day.year)
    except SourceUnavailableError:
        indicators = []
    exchange, _ = await get_exchange(day)
    editorial, _ = await editorial_domain.build_editorial(day, events, indicators, exchange)
    return editorial
