import datetime as dt
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Source = Literal["wikipedia", "nasa", "worldbank", "alphavantage", "ipeadata", "llm", "openmeteo"]


class SourceStatus(BaseModel):
    source: Source
    ok: bool
    cached: bool = Field(False, description="True if the answer came from the local cache.")
    message: str | None = Field(None, description="Failure reason (pt-BR) when ok=False.")


class ApiError(BaseModel):
    detail: str = Field(description="Friendly pt-BR message, ready to show to the user.")
    source: Source | None = None


class Event(BaseModel):
    id: str = Field(
        description="Short id, stable within a front page (e.g. 'e3'); the LLM cites it."
    )
    layer: Literal["day", "month", "on_this_day"]
    year: int | None = None
    date: dt.date | None = Field(None, description="Exact date, when known.")
    text: str
    url: str | None = Field(None, description="Related Wikipedia article.")
    image_url: str | None = None
    mentions_brazil: bool = False
    score: float = Field(0, description="Ranking weight (layer + bonuses).")


class Birth(BaseModel):
    year: int
    text: str = Field(description="pt-BR, e.g. 'Ayrton Senna, piloto brasileiro.'")
    url: str | None = None
    image_url: str | None = None
    mentions_brazil: bool = False


class Headline(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    subtitle: str | None = None
    event_id: str = Field(description="Must exist in `FrontPage.events`; otherwise it is dropped.")


class LLMEditorial(BaseModel):
    model_config = ConfigDict(extra="forbid")

    headlines: list[Headline]
    title: str = Field(description="Editorial title (pt-BR).")
    body: str = Field(
        description="Editorial in pt-BR, 2 to 4 paragraphs separated by a blank line."
    )


class Editorial(LLMEditorial):
    ai_generated: bool = Field(
        description="False when the LLM failed and headlines were built from the raw event text."
    )
    model: str | None = Field(
        None, description="Model that wrote it (e.g. anthropic/claude-haiku-5.5)."
    )


class SeriesPoint(BaseModel):
    year: int
    value: float


class Indicator(BaseModel):
    code: str = Field(description="World Bank code (e.g. SP.POP.TOTL).")
    name: str = Field(description="Short pt-BR name for display (e.g. 'População').")
    unit: str = Field(description="Display unit in pt-BR (e.g. 'habitantes', '%', 'US$', 'anos').")
    then_year: int
    then_value: float
    now_year: int
    now_value: float
    series: list[SeriesPoint] = Field(
        default_factory=list, description="Yearly series for the sparkline."
    )


class Currency(BaseModel):
    name: str = Field(description="pt-BR name, e.g. 'Cruzeiro Novo'.")
    symbol: str = Field(description="E.g. 'NCr$'.")
    start: dt.date
    end: dt.date | None = None


class Exchange(BaseModel):
    currency: Currency
    usd_then: float | None = Field(None, description="Value of US$ 1 at the time.")
    usd_then_period: str | None = Field(None, description="Rate period: 'YYYY-MM' or 'YYYY'.")
    usd_then_source: Literal["alphavantage", "worldbank"] | None = None
    usd_now: float | None = Field(None, description="US$ 1 in reais, latest month (Alpha Vantage).")
    usd_now_period: str | None = None
    note: str | None = Field(None, description="pt-BR note shown under the numbers.")


class Money(BaseModel):
    currency_symbol: str = Field(description="Symbol of the currency of the time, e.g. 'Cr$'.")
    period: str | None = Field(None, description="Month used for 'then', 'YYYY-MM'.")
    min_wage_then: float | None = Field(None, description="Minimum wage, in money of the time.")
    min_wage_then_today: float | None = Field(
        None, description="That minimum wage in today's reais (price-corrected)."
    )
    min_wage_now: float | None = Field(None, description="Current minimum wage in reais.")
    amount_then: float | None = Field(
        None, description="A round amount in money of the time (power of ten), e.g. 100."
    )
    amount_today: float | None = Field(None, description="`amount_then` in today's reais.")
    today_period: str | None = Field(None, description="Month of today's prices, 'YYYY-MM'.")
    note: str | None = Field(None, description="pt-BR note shown under the numbers.")


class MoonPhaseDate(BaseModel):
    phase: str = Field(description="pt-BR main phase: Nova, Quarto crescente, Cheia...")
    date: dt.date = Field(description="Day of the phase in Brasília.")


class Moon(BaseModel):
    date: dt.date
    phase: str = Field(description="pt-BR phase name, e.g. 'Crescente gibosa'.")
    phase_angle: float = Field(description="0-360 degrees: 0 new, 90 first quarter, 180 full.")
    illumination: float = Field(description="Illuminated share of the disc, 0-1.")
    waxing: bool = Field(description="True from new to full (lit on the LEFT, seen from Brazil).")
    next_phases: list[MoonPhaseDate] = Field(default_factory=list)


class SkyObject(BaseModel):
    name: str = Field(description="pt-BR name, e.g. 'Júpiter', 'Acrux'.")
    kind: Literal["star", "planet", "moon"]
    azimuth: float = Field(description="Degrees from north, clockwise (90 = east).")
    altitude: float = Field(description="Degrees above the horizon (negative = below it).")
    magnitude: float | None = Field(None, description="Visual magnitude (lower = brighter).")


class Constellation(BaseModel):
    name: str = Field(description="pt-BR name, e.g. 'Cruzeiro do Sul'.")
    lines: list[list[str]] = Field(description="Pairs of star names joined on the chart.")


class SkyTip(BaseModel):
    symbol: str = Field(description="Almanac symbol: ☾, ♂, ♃, ✢...")
    title: str = Field(description="pt-BR name, e.g. 'Lua crescente'.")
    detail: str = Field(description="Where to look, pt-BR sentence ending with a period.")


class Sky(BaseModel):
    date: dt.date
    objects: list[SkyObject]
    constellations: list[Constellation] = Field(default_factory=list)
    guide: list[SkyTip] = Field(
        default_factory=list,
        description="'O que olhar': the Moon, visible planets and the Southern Cross in words.",
    )


class City(BaseModel):
    slug: str = Field(
        description="Identifier used in `?city=`: a preset ('rio-grande') or 'geo-<id>' "
        "for a city found with /api/cities/search."
    )
    name: str
    state: str = Field(description="State/region, e.g. 'RS' or 'Rio Grande do Sul'.")
    country: str | None = Field(None, description="Country name in pt-BR (searched cities).")


class HourlyPoint(BaseModel):
    hour: int = Field(description="0-23, local time (São Paulo).")
    temperature: float | None = Field(None, description="°C")
    precipitation: float | None = Field(None, description="mm in the hour")
    humidity: float | None = Field(None, description="Relative humidity, %")
    wind: float | None = Field(None, description="Wind speed at 10 m, km/h")


class Weather(BaseModel):
    city: City
    date: dt.date
    temp_max: float | None = Field(None, description="°C")
    temp_min: float | None = Field(None, description="°C")
    precipitation_mm: float | None = None
    wind_max_kmh: float | None = None
    weather_code: int | None = Field(None, description="WMO weather code.")
    description: str = Field(description="pt-BR summary of the weather code.")
    hourly: list[HourlyPoint] = Field(default_factory=list)


class FrontPage(BaseModel):
    date: dt.date
    issue_number: int = Field(description="Days since 1900-01-01, plus 1.")
    events: list[Event]
    indicators: list[Indicator] = Field(default_factory=list)
    exchange: Exchange | None = None
    editorial: Editorial | None = None
    births: list[Birth] = Field(default_factory=list)
    deaths: list[Birth] = Field(default_factory=list)
    money: Money | None = None
    # Desativado: Lua e céu noturno
    # moon: Moon | None = None
    # sky: Sky | None = None
    sources: list[SourceStatus]
    generated_at: dt.datetime


class EditorialRequest(BaseModel):
    date: dt.date


class Health(BaseModel):
    status: Literal["ok"]
    llm_model: str
    alphavantage_calls_left: int = Field(
        description="Alpha Vantage calls left today (our own cap)."
    )
