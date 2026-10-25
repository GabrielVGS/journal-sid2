import asyncio
import unicodedata
from datetime import date
from typing import Any

from app.core.cache import DAY, cached
from app.core.errors import InvalidInputError, SourceUnavailableError
from app.core.http import get_json
from app.schemas import City, HourlyPoint, Weather

URL = "https://archive-api.open-meteo.com/v1/archive"
GEOCODING_SEARCH_URL = "https://geocoding-api.open-meteo.com/v1/search"
GEOCODING_GET_URL = "https://geocoding-api.open-meteo.com/v1/get"
MAX_SEARCH_RESULTS = 8
FIRST_DATE = date(1940, 1, 1)
DAILY_FIELDS = (
    "temperature_2m_max,temperature_2m_min,precipitation_sum,weather_code,wind_speed_10m_max"
)
HOURLY_FIELDS = "temperature_2m,precipitation,relative_humidity_2m,wind_speed_10m"

# Cidades sugeridas: nome, UF, latitude e longitude.
CITIES: dict[str, tuple[str, str, float, float]] = {
    "rio-grande": ("Rio Grande", "RS", -32.035, -52.099),
    "pelotas": ("Pelotas", "RS", -31.772, -52.343),
    "porto-alegre": ("Porto Alegre", "RS", -30.033, -51.230),
    "florianopolis": ("Florianópolis", "SC", -27.595, -48.548),
    "curitiba": ("Curitiba", "PR", -25.429, -49.271),
    "sao-paulo": ("São Paulo", "SP", -23.550, -46.633),
    "rio-de-janeiro": ("Rio de Janeiro", "RJ", -22.907, -43.173),
    "belo-horizonte": ("Belo Horizonte", "MG", -19.917, -43.934),
    "brasilia": ("Brasília", "DF", -15.794, -47.882),
    "goiania": ("Goiânia", "GO", -16.686, -49.265),
    "salvador": ("Salvador", "BA", -12.971, -38.501),
    "recife": ("Recife", "PE", -8.048, -34.877),
    "fortaleza": ("Fortaleza", "CE", -3.732, -38.527),
    "belem": ("Belém", "PA", -1.456, -48.490),
    "manaus": ("Manaus", "AM", -3.119, -60.022),
}
DEFAULT_CITY = "rio-grande"

# Códigos de tempo da OMM traduzidos para português.
_WEATHER_CODES: list[tuple[range, str]] = [
    (range(0, 1), "Céu limpo"),
    (range(1, 3), "Parcialmente nublado"),
    (range(3, 4), "Nublado"),
    (range(45, 49), "Nevoeiro"),
    (range(51, 58), "Garoa"),
    (range(61, 68), "Chuva"),
    (range(71, 78), "Neve"),
    (range(80, 83), "Pancadas de chuva"),
    (range(85, 87), "Pancadas de neve"),
    (range(95, 100), "Trovoadas"),
]


@cached("openmeteo:geo_search", ttl=30 * DAY)
async def search_raw(query: str, country: str | None = None) -> list[dict[str, Any]]:
    params: dict[str, Any] = {"name": query, "count": 20, "language": "pt", "format": "json"}
    if country:
        params["countryCode"] = country
    body = await get_json("openmeteo", GEOCODING_SEARCH_URL, params=params)
    results: list[dict[str, Any]] = body.get("results") or []
    return results


@cached("openmeteo:geo_get", ttl=365 * DAY)
async def place_raw(place_id: int) -> dict[str, Any]:
    body: dict[str, Any] = await get_json(
        "openmeteo", GEOCODING_GET_URL, params={"id": place_id, "language": "pt"}
    )
    return body


def _plain(text: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", text.lower()) if not unicodedata.combining(c)
    )


def _place_city(place: dict[str, Any]) -> City:
    return City(
        slug=f"geo-{place['id']}",
        name=place["name"],
        state=place.get("admin1") or "",
        country=place.get("country"),
    )


# Busca no Brasil e no mundo em paralelo; cidades brasileiras aparecem primeiro.
async def search_cities(query: str) -> list[City]:
    query = query.strip()
    if not 2 <= len(query) <= 60:
        raise InvalidInputError("Digite de 2 a 60 letras para buscar a cidade.")
    brazil, world = await asyncio.gather(search_raw(query.lower(), "BR"), search_raw(query.lower()))
    typed = _plain(query)

    def rank(place: dict[str, Any]) -> tuple[bool, int]:
        return typed not in _plain(place["name"]), -(place.get("population") or 0)

    by_population = sorted(brazil, key=rank) + sorted(world, key=rank)
    seen: set[int] = set()
    unique = []
    for place in by_population:
        if place["id"] not in seen:
            seen.add(place["id"])
            unique.append(place)
    return [_place_city(place) for place in unique[:MAX_SEARCH_RESULTS]]


# Cidades buscadas usam o slug geo-<id> da geocodificação.
async def resolve_city(slug: str) -> tuple[City, float, float]:
    if slug in CITIES:
        name, state, latitude, longitude = CITIES[slug]
        return City(slug=slug, name=name, state=state, country="Brasil"), latitude, longitude
    if slug.startswith("geo-") and slug[4:].isdigit():
        try:
            place = await place_raw(int(slug[4:]))
        except SourceUnavailableError:
            raise InvalidInputError("Cidade não encontrada.") from None
        if "latitude" in place:
            return _place_city(place), place["latitude"], place["longitude"]
    raise InvalidInputError("Cidade não encontrada.")


def list_cities() -> list[City]:
    return [
        City(slug=slug, name=name, state=state, country="Brasil")
        for slug, (name, state, _, _) in CITIES.items()
    ]


def describe(code: int | None) -> str:
    if code is None:
        return "Sem registro"
    return next((text for codes, text in _WEATHER_CODES if code in codes), "Tempo variável")


@cached("openmeteo:day_local_tz", ttl=30 * DAY)
async def fetch_day_raw(latitude: float, longitude: float, day: str) -> dict[str, Any]:
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": day,
        "end_date": day,
        "daily": DAILY_FIELDS,
        "hourly": HOURLY_FIELDS,
        # Horas no fuso da própria cidade.
        "timezone": "auto",
    }
    body: dict[str, Any] = await get_json("openmeteo", URL, params=params)
    if body.get("error") or "daily" not in body:
        raise SourceUnavailableError(
            "openmeteo", str(body.get("reason", "unexpected answer"))[:120]
        )
    return body


def _first(daily: dict[str, Any], field: str) -> Any:
    values = daily.get(field) or [None]
    return values[0]


async def get_weather(day: date, city_slug: str = DEFAULT_CITY) -> Weather:
    if day < FIRST_DATE:
        raise InvalidInputError("Os registros de clima começam em 1940.")
    city, latitude, longitude = await resolve_city(city_slug)
    raw = await fetch_day_raw(latitude, longitude, day.isoformat())
    daily, hourly = raw["daily"], raw.get("hourly", {})
    code = _first(daily, "weather_code")
    return Weather(
        city=city,
        date=day,
        temp_max=_first(daily, "temperature_2m_max"),
        temp_min=_first(daily, "temperature_2m_min"),
        precipitation_mm=_first(daily, "precipitation_sum"),
        wind_max_kmh=_first(daily, "wind_speed_10m_max"),
        weather_code=code,
        description=describe(code),
        hourly=[
            HourlyPoint(hour=int(time[11:13]), temperature=t, precipitation=p, humidity=h, wind=w)
            for time, t, p, h, w in zip(
                hourly.get("time", []),
                hourly.get("temperature_2m", []),
                hourly.get("precipitation", []),
                hourly.get("relative_humidity_2m", []),
                hourly.get("wind_speed_10m", []),
                strict=False,
            )
        ],
    )
