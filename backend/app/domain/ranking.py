import datetime as dt
import re
from dataclasses import dataclass, field, replace
from typing import Literal

from app.schemas import Event

Layer = Literal["day", "month", "on_this_day"]

# Pesos do ranking: dia exato > mesmo mês > mesmo dia em outros anos.
LAYER_WEIGHT: dict[Layer, float] = {"day": 3, "month": 2, "on_this_day": 1}
BRAZIL_BONUS = 1.0
SELECTED_BONUS = 0.5
MAX_ON_THIS_DAY = 12

# Menção ao Brasil: palavras que começam com "brasil" ou "brasileir".
_BRAZIL = re.compile(r"\bbrasil|\bbrasileir", re.IGNORECASE)
_GENERIC_LINKS = frozenset({"Brasil", "Estados Unidos", "Portugal"})


@dataclass(frozen=True)
class RawEvent:
    layer: Layer
    text: str
    year: int | None = None
    date: dt.date | None = None
    url: str | None = None
    image_url: str | None = None
    about_brazil: bool = False
    selected: bool = False
    links: frozenset[str] = field(default_factory=frozenset)

    @property
    def mentions_brazil(self) -> bool:
        return self.about_brazil or bool(_BRAZIL.search(self.text))


def score(event: RawEvent) -> float:
    return (
        LAYER_WEIGHT[event.layer]
        + (BRAZIL_BONUS if event.mentions_brazil else 0)
        + (SELECTED_BONUS if event.selected else 0)
    )


# Mesmo evento vindo de fontes diferentes: mesma data e um artigo citado em comum.
def is_same_event(a: RawEvent, b: RawEvent) -> bool:
    if a.date is None or a.date != b.date:
        return False
    return bool((a.links & b.links) - _GENERIC_LINKS) or a.text == b.text


# Mantém o de maior pontuação e junta as informações do outro.
def merge(a: RawEvent, b: RawEvent) -> RawEvent:
    best, other = (a, b) if score(a) >= score(b) else (b, a)
    return replace(
        best,
        about_brazil=best.about_brazil or other.about_brazil,
        selected=best.selected or other.selected,
        url=best.url or other.url,
        image_url=best.image_url or other.image_url,
        links=best.links | other.links,
    )


def deduplicate(events: list[RawEvent]) -> list[RawEvent]:
    unique: list[RawEvent] = []
    for event in events:
        for index, kept in enumerate(unique):
            if is_same_event(kept, event):
                unique[index] = merge(kept, event)
                break
        else:
            unique.append(event)
    return unique


# Ordena por pontuação, limita as efemérides e numera os eventos (e1, e2, ...).
def rank(events: list[RawEvent], max_on_this_day: int = MAX_ON_THIS_DAY) -> list[Event]:
    ordered = sorted(deduplicate(events), key=lambda e: (-score(e), -(e.year or 0)))
    on_this_day = [e for e in ordered if e.layer == "on_this_day"][:max_on_this_day]
    kept = [e for e in ordered if e.layer != "on_this_day" or e in on_this_day]
    return [
        Event(
            id=f"e{position}",
            layer=e.layer,
            year=e.year,
            date=e.date,
            text=e.text,
            url=e.url,
            image_url=e.image_url,
            mentions_brazil=e.mentions_brazil,
            score=score(e),
        )
        for position, e in enumerate(kept, start=1)
    ]
