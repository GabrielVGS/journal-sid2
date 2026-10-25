import re
from datetime import date
from typing import TypedDict

from pydantic import BaseModel, ConfigDict, Field

from app.core.cache import DAY, cached
from app.core.text import truncate
from app.domain.ranking import RawEvent
from app.services.llm.factory import get_llm_client
from app.services.wikitext import article_url, clean_wikitext, fetch_wikitext

# Abaixo disso de notícias do dia em português, busca na Wikipedia em inglês.
MIN_PT_DAY_EVENTS = 3
MAX_CANDIDATES = 15
MAX_TRANSLATED = 6
MIN_WORDS = 6

MONTHS_EN = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
]

# Título de nível 2, ex.: "== April 5, 2002 ==". Grupo: o texto do título.
_LEVEL2_HEADING = re.compile(r"^==([^=].*?)==\s*$", re.MULTILINE)
# Conteúdo da seção "== Events ==" até o próximo título de nível 2 ou o fim.
_EVENTS_SECTION = re.compile(r"^==\s*Events\s*==\s*$(.*?)(?=^==[^=]|\Z)", re.MULTILINE | re.DOTALL)


class EnglishItem(TypedDict):
    text: str
    url: str | None
    links: list[str]


class TranslatedItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    index: int = Field(description="Index of the original item in the list.")
    text: str = Field(description="One pt-BR sentence, faithful to the original.")


class TranslatedEvents(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[TranslatedItem]


TRANSLATION_PROMPT = """Você traduz notícias para um jornal brasileiro.
Para cada fato escolhido, escreva UMA frase em português do Brasil (até 250 caracteres),
fiel ao original: não acrescente nomes, números ou detalhes que não estejam no texto.
Escolha no máximo {limit} fatos, priorizando importância histórica e interesse para leitores
brasileiros. Omita fatos que repetem algum destes, já publicados:
{known}
Responda com "items": a lista de {{"index": número do fato original, "text": tradução}}."""


def _bullets(wikitext: str) -> list[tuple[str, tuple[str, ...]]]:
    items = []
    for line in wikitext.splitlines():
        if not line.lstrip().startswith("*"):
            continue
        text, links = clean_wikitext(line.lstrip("*").strip())
        if text.startswith("Born"):
            continue
        if len(text.split()) >= MIN_WORDS:
            items.append((truncate(text, 500), links))
    return items


def month_article_day(wikitext: str, day: date) -> str:
    # Título do dia na página do mês, ex.: "April 5, 2002 (Friday)".
    pattern = re.compile(rf"\b{MONTHS_EN[day.month - 1]}\s+{day.day}\b.*\b{day.year}\b")
    headings = list(_LEVEL2_HEADING.finditer(wikitext))
    for index, heading in enumerate(headings):
        if pattern.search(heading.group(1).replace("[", "").replace("]", "")):
            end = headings[index + 1].start() if index + 1 < len(headings) else len(wikitext)
            return wikitext[heading.end() : end]
    return ""


def year_article_day(wikitext: str, day: date) -> str:
    section = _EVENTS_SECTION.search(wikitext)
    wikitext = section.group(1) if section else ""
    # Item da página do ano com o link do dia, ex.: "* [[April 5]] – texto".
    # Grupo: o texto (vazio quando os eventos vêm nos subitens "**").
    date_link = re.compile(
        rf"^\*\s*\[\[{MONTHS_EN[day.month - 1]} {day.day}\]\]\s*(?:[–—:-]\s*)?(.*)$"
    )
    lines, inside = [], False
    for line in wikitext.splitlines():
        if match := date_link.match(line.strip()):
            inside = not match.group(1).strip()
            if match.group(1).strip():
                lines.append("* " + match.group(1))
        elif inside and line.startswith("**"):
            lines.append(line)
        else:
            inside = False
    return "\n".join(lines)


# Tenta, em ordem: página do mês, Portal:Current events e página do ano.
async def english_candidates(day: date) -> list[tuple[str, tuple[str, ...]]]:
    month_name = MONTHS_EN[day.month - 1]
    sources = [
        (f"{month_name} {day.year}", month_article_day),
        (f"Portal:Current events/{day.year} {month_name} {day.day}", lambda text, _: text),
        (str(day.year), year_article_day),
    ]
    for page, extract in sources:
        items = _bullets(extract(await fetch_wikitext(page, lang="en"), day))
        if items:
            return items[:MAX_CANDIDATES]
    return []


# O LLM traduz e devolve o índice de cada fato, para manter o link original.
@cached("wikipedia:en_day", ttl=30 * DAY)
async def translated_day_events(day_iso: str, known: list[str]) -> list[EnglishItem]:
    day = date.fromisoformat(day_iso)
    candidates = await english_candidates(day)
    if not candidates:
        return []
    numbered = "\n".join(f"{index}. {text}" for index, (text, _) in enumerate(candidates))
    known_text = "\n".join(f"- {text}" for text in known) or "- (nenhum)"
    system = TRANSLATION_PROMPT.format(limit=MAX_TRANSLATED, known=known_text)
    result = await get_llm_client().generate(
        system, f"FATOS EM INGLÊS:\n{numbered}", TranslatedEvents
    )
    events: list[EnglishItem] = []
    seen: set[int] = set()
    for item in result.value.items[:MAX_TRANSLATED]:
        if not 0 <= item.index < len(candidates) or item.index in seen:
            continue
        seen.add(item.index)
        _, links = candidates[item.index]
        events.append(
            {
                "text": truncate(item.text.strip(), 300),
                "url": article_url(links[0], lang="en") if links else None,
                "links": list(links),
            }
        )
    return events


async def english_day_events(day: date, known: list[str]) -> list[RawEvent]:
    items = await translated_day_events(day.isoformat(), known)
    return [
        RawEvent(
            layer="day",
            text=item["text"],
            year=day.year,
            date=day,
            url=item["url"],
            links=frozenset(f"en:{link}" for link in item["links"]),
        )
        for item in items
    ]
