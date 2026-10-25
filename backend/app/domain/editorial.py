import logging
from datetime import date

from app.core import cache
from app.core.errors import SourceUnavailableError
from app.core.text import truncate
from app.schemas import Editorial, Event, Exchange, Headline, Indicator, LLMEditorial
from app.services.llm.base import LLMClient
from app.services.llm.factory import get_llm_client
from app.services.llm.prompts import build_editorial_prompt

logger = logging.getLogger(__name__)

MAX_FACTS = 20
PERSIST_TTL = 3650 * cache.DAY
FALLBACK_TITLE = "Edição sem editorial"
FALLBACK_BODY = "Nosso editorialista não conseguiu fechar o texto a tempo desta edição."


# Evita anacronismo: o LLM só recebe fatos que já tinham acontecido na data.
def eligible_facts(day: date, events: list[Event]) -> list[Event]:
    known = [
        e
        for e in events
        if (e.date is None or e.date <= day) and (e.year is None or e.year <= day.year)
    ]
    return known[:MAX_FACTS]


def headlines_from_events(events: list[Event], limit: int = 3) -> list[Headline]:
    return [Headline(title=truncate(e.text, 90), event_id=e.id) for e in events[:limit]]


# Sem LLM, as manchetes saem do próprio texto dos eventos.
def fallback_editorial(facts: list[Event]) -> Editorial:
    return Editorial(
        headlines=headlines_from_events(facts),
        title=FALLBACK_TITLE,
        body=FALLBACK_BODY,
        ai_generated=False,
    )


# Descarta manchetes que citam um id inexistente; efemérides só se não houver notícia.
def validate_headlines(answer: LLMEditorial, facts: list[Event]) -> list[Headline]:
    news = [e for e in facts if e.layer != "on_this_day"]
    known = {e.id for e in news or facts}
    valid = [h for h in answer.headlines if h.event_id in known]
    dropped = len(answer.headlines) - len(valid)
    if dropped:
        logger.warning("Dropped %d headline(s) citing unknown events", dropped)
    return valid or headlines_from_events(news or facts)


def _key(day: date) -> str:
    return f"editorial:{day.isoformat()}"


async def load_stored(day: date) -> Editorial | None:
    stored = await cache.read(_key(day))
    return Editorial.model_validate(stored) if stored is not None else None


async def build_editorial(
    day: date,
    events: list[Event],
    indicators: list[Indicator],
    exchange: Exchange | None,
    client: LLMClient | None = None,
) -> tuple[Editorial, SourceUnavailableError | None]:
    # O editorial é gerado uma única vez por data e fica salvo.
    stored = await load_stored(day)
    if stored is not None:
        return stored, None

    facts = eligible_facts(day, events)
    if not facts:
        return fallback_editorial(facts), None
    system, user = build_editorial_prompt(day, facts, indicators, exchange)
    try:
        result = await (client or get_llm_client()).generate(system, user, LLMEditorial)
    except SourceUnavailableError as exc:
        return fallback_editorial(facts), exc

    editorial = Editorial(
        headlines=validate_headlines(result.value, facts),
        title=result.value.title,
        body=result.value.body,
        ai_generated=True,
        model=result.model,
    )
    await cache.write(_key(day), editorial.model_dump(mode="json"), PERSIST_TTL)
    return editorial, None
