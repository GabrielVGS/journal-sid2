import asyncio
import logging
import re
from dataclasses import dataclass
from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.core import dates
from app.core.cache import DAY, cached
from app.core.errors import SourceUnavailableError
from app.core.http import get_json
from app.core.text import truncate
from app.domain.ranking import RawEvent, rank
from app.schemas import Birth, Event
from app.services import wikipedia_en
from app.services.llm.factory import get_llm_client
from app.services.wikitext import (
    article_url,
    clean_wikitext,
    fetch_wikitext,
)

# Feed "neste dia" da Wikipedia em português; a segunda URL é reserva.
FEED_URLS = [
    "https://api.wikimedia.org/feed/v1/wikipedia/pt/onthisday/all/{month:02d}/{day:02d}",
    "https://pt.wikipedia.org/api/rest_v1/feed/onthisday/all/{month:02d}/{day:02d}",
]
MAX_TEXT = 400

logger = logging.getLogger(__name__)

MONTHS = {name: number for number, name in enumerate(dates.MONTH_NAMES, start=1)}

# Referências do wikitext: <ref name=x /> ou <ref>...</ref>.
_REF = re.compile(r"<ref[^>/]*/>|<ref[^>]*>.*?</ref>", re.DOTALL | re.IGNORECASE)
# Comentários HTML <!-- ... -->.
_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
# Conteúdo da seção "== Eventos ==" até o próximo título de nível 2 ou o fim.
_SECTION = re.compile(r"^==\s*Eventos\s*==\s*$(.*?)(?=^==[^=]|\Z)", re.MULTILINE | re.DOTALL)
# Subtítulo com o nome do mês, ex.: "=== Julho ===". Grupo: o mês.
_MONTH_HEADING = re.compile(r"^===+\s*([A-Za-zçÇ]+)\s*===+\s*$")
# Link de data: [[20 de julho]] ou [[1º de julho|1º]]. Grupos: dia e mês.
_DATE_LINK = re.compile(r"\[\[(\d{1,2})(?:º|\.º)? de ([a-zç]+)(?:\|[^\]]*)?\]\]", re.IGNORECASE)
# Item de lista que começa com links de data, ex.: "* [[1 de julho]]: texto".
# Grupos: os asteriscos (nível), os links de data e o texto depois de ":" ou "–".
_DATED_LINE = re.compile(r"^(\*+)\s*((?:\[\[[^\]]+\]\][\s,e]*)+?)\s*(?:[:\-–—]\s*|$)(.*)$")
# Frase que começa com "Em março". Grupo: o mês.
_IN_MONTH = re.compile(r"^Em ([a-zç]+)\b", re.IGNORECASE)
# Data sem link no começo do item, ex.: "1º de julho: texto". Grupos: dia, mês e texto.
_PLAIN_DATE = re.compile(r"^(\d{1,2})(?:º|\.º)? de ([a-zç]+)\s*[:\-–—]\s*(.*)$", re.IGNORECASE)


@cached("wikipedia:onthisday", ttl=30 * DAY)
async def fetch_on_this_day_raw(month: int, day: int) -> dict[str, Any]:
    primary, fallback = (url.format(month=month, day=day) for url in FEED_URLS)
    try:
        body: dict[str, Any] = await get_json("wikipedia", primary)
    except SourceUnavailableError:
        body = await get_json("wikipedia", fallback)
    return body


def _page_url(pages: list[dict[str, Any]]) -> str | None:
    return next(
        (p["content_urls"]["desktop"]["page"] for p in pages if p.get("content_urls")), None
    )


def _page_image(pages: list[dict[str, Any]]) -> str | None:
    return next((p["thumbnail"]["source"] for p in pages if p.get("thumbnail")), None)


# Eventos do mesmo ano viram "dia"; os de outros anos, efemérides.
def parse_feed(raw: dict[str, Any], day: date) -> list[RawEvent]:
    events = []
    for key in ("selected", "events"):
        for item in raw.get(key, []):
            year = item.get("year")
            if not isinstance(year, int) or not item.get("text"):
                continue
            pages = item.get("pages") or []
            titles = [p["titles"]["normalized"] for p in pages if p.get("titles")]
            image, url = _page_image(pages), _page_url(pages)
            try:
                event_date: date | None = day.replace(year=year)
            except ValueError:
                event_date = None
            events.append(
                RawEvent(
                    layer="day" if year == day.year else "on_this_day",
                    text=truncate(item["text"].strip(), MAX_TEXT),
                    year=year,
                    date=event_date,
                    url=url,
                    image_url=image,
                    selected=key == "selected",
                    links=frozenset(titles),
                )
            )
    return events


MAX_PEOPLE = 8
# Menção ao Brasil: palavras que começam com "brasil" ou "brasileir".
_BRAZIL = re.compile(r"\bbrasil|\bbrasileir", re.IGNORECASE)

PeopleKind = Literal["births", "deaths"]
_KIND_VERB: dict[PeopleKind, str] = {"births": "nascidas", "deaths": "mortas"}


def parse_people(
    raw: dict[str, Any], kind: PeopleKind = "births", limit: int | None = MAX_PEOPLE
) -> list[Birth]:
    people = []
    for item in raw.get(kind, []):
        if not isinstance(item.get("year"), int) or not item.get("text"):
            continue
        pages = item.get("pages") or []
        people.append(
            Birth(
                year=item["year"],
                text=truncate(item["text"].strip(), 200),
                url=next(
                    (p["content_urls"]["desktop"]["page"] for p in pages if p.get("content_urls")),
                    None,
                ),
                image_url=next(
                    (p["thumbnail"]["source"] for p in pages if p.get("thumbnail")), None
                ),
                mentions_brazil=bool(_BRAZIL.search(item["text"])),
            )
        )
    return sorted(people, key=lambda b: (not b.mentions_brazil, b.image_url is None))[:limit]


class FamousPick(BaseModel):
    model_config = ConfigDict(extra="forbid")

    indexes: list[int] = Field(description="Indexes of the chosen people in the list.")


FAMOUS_PROMPT = """Abaixo estão pessoas {verb} em {day}, de vários anos.
Escolha as {limit} mais conhecidas do público brasileiro em geral (inclua brasileiras se
houver alguma realmente famosa). Responda só com "indexes": os números da lista."""


# O LLM escolhe, por índice, as pessoas mais conhecidas da lista.
@cached("wikipedia:famous_people", ttl=30 * DAY)
async def famous_indexes(month: int, day: int, kind: PeopleKind, lines: list[str]) -> list[int]:
    numbered = "\n".join(f"{index}. {line}" for index, line in enumerate(lines))
    label = f"{day} de {dates.MONTH_NAMES[month - 1]}"
    system = FAMOUS_PROMPT.format(verb=_KIND_VERB[kind], day=label, limit=MAX_PEOPLE)
    result = await get_llm_client().generate(system, numbered, FamousPick)
    valid = [i for i in dict.fromkeys(result.value.indexes) if 0 <= i < len(lines)]
    return valid[:MAX_PEOPLE]


async def get_people(day: date, kind: PeopleKind) -> list[Birth]:
    raw = await fetch_on_this_day_raw(day.month, day.day)
    everyone = parse_people(raw, kind, limit=None)
    try:
        lines = [f"{person.year} – {person.text}" for person in everyone]
        indexes = await famous_indexes(day.month, day.day, kind, lines) if lines else []
        chosen = [everyone[i] for i in indexes]
    except Exception:
        logger.warning("Famous %s selection failed for %s", kind, day, exc_info=True)
        # Se o LLM falhar, usa a ordem padrão (brasileiros e com foto primeiro).
        chosen = everyone[:MAX_PEOPLE]
    return sorted(chosen or everyone[:MAX_PEOPLE], key=lambda b: -b.year)


async def get_births(day: date) -> list[Birth]:
    return await get_people(day, "births")


async def get_deaths(day: date) -> list[Birth]:
    return await get_people(day, "deaths")


@dataclass(frozen=True)
class WikiLine:
    month: int
    day: int | None
    text: str
    links: tuple[str, ...]


def events_section(wikitext: str) -> str:
    match = _SECTION.search(wikitext)
    if not match:
        return ""
    return _COMMENT.sub("", _REF.sub("", match.group(1)))


# Lê a seção "Eventos" das páginas de ano, linha a linha, descobrindo o dia e o mês.
def parse_event_lines(wikitext: str) -> list[WikiLine]:
    lines: list[WikiLine] = []
    heading_month: int | None = None
    parent: tuple[int, int | None] | None = None
    for raw_line in events_section(wikitext).splitlines():
        line = raw_line.strip()
        if heading := _MONTH_HEADING.match(line):
            heading_month = MONTHS.get(heading.group(1).lower())
            continue
        if not line.startswith("*"):
            continue
        month: int | None = None
        day: int | None = None
        body = line.lstrip("*").strip()
        dated = _DATED_LINE.match(line)
        first_date = _DATE_LINK.search(dated.group(2)) if dated else None
        if dated and first_date:
            day, month = int(first_date.group(1)), MONTHS.get(first_date.group(2).lower())
            body = dated.group(3)
            if not line.startswith("**"):
                parent = (month, day) if month else None
        elif plain := _PLAIN_DATE.match(body):
            day, month = int(plain.group(1)), MONTHS.get(plain.group(2).lower())
            body = plain.group(3)
        elif line.startswith("**") and parent:
            month, day = parent
        elif in_month := _IN_MONTH.match(body):
            month = MONTHS.get(in_month.group(1).lower())
        else:
            month = heading_month
        text, links = clean_wikitext(body)
        if month and text:
            lines.append(WikiLine(month=month, day=day, text=truncate(text, MAX_TEXT), links=links))
    return lines


def lines_to_events(lines: list[WikiLine], day: date, about_brazil: bool) -> list[RawEvent]:
    events = []
    for line in lines:
        if line.month != day.month:
            continue
        try:
            line_date = date(day.year, line.month, line.day) if line.day else None
        except ValueError:
            line_date = None
        exact = line_date == day
        main_link = line.links[0] if line.links else None
        events.append(
            RawEvent(
                layer="day" if exact else "month",
                text=line.text,
                year=day.year,
                date=line_date,
                url=article_url(main_link) if main_link else None,
                about_brazil=about_brazil,
                links=frozenset(line.links),
            )
        )
    return events


# Junta o feed, "<ano> no Brasil" e "<ano>"; com poucas notícias, usa a Wikipedia em inglês.
async def get_events(day: date) -> list[Event]:
    feed, brazil_page, year_page = await asyncio.gather(
        fetch_on_this_day_raw(day.month, day.day),
        fetch_wikitext(f"{day.year} no Brasil"),
        fetch_wikitext(str(day.year)),
        return_exceptions=True,
    )
    raw: list[RawEvent] = []
    if not isinstance(feed, BaseException):
        raw += parse_feed(feed, day)
    if not isinstance(brazil_page, BaseException):
        raw += lines_to_events(parse_event_lines(brazil_page), day, about_brazil=True)
    if not isinstance(year_page, BaseException):
        raw += lines_to_events(parse_event_lines(year_page), day, about_brazil=False)
    if all(isinstance(result, BaseException) for result in (feed, brazil_page, year_page)):
        raise SourceUnavailableError("wikipedia", "no Wikipedia source answered")
    day_texts = [event.text for event in raw if event.layer == "day"]
    if len(day_texts) < wikipedia_en.MIN_PT_DAY_EVENTS:
        try:
            raw += await wikipedia_en.english_day_events(day, day_texts)
        except Exception:
            logger.warning("English Wikipedia fallback failed for %s", day, exc_info=True)
    return rank(raw)
