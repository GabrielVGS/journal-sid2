import logging
import re
from dataclasses import dataclass
from datetime import date
from html import escape

from app.core import dates
from app.core.errors import InvalidDateError
from app.domain import editorial, front_page
from app.schemas import FrontPage

logger = logging.getLogger(__name__)

SITE_NAME = "O Jornal do Dia"
DEFAULT_DESCRIPTION = "Digite uma data e receba a capa do jornal daquele dia."
DEFAULT_IMAGE = "/og-default.png"
MAX_DESCRIPTION = 200

# Marcadores no index.html onde as tags Open Graph são inseridas.
_BLOCK = re.compile(r"<!-- og -->.*?<!-- /og -->", re.DOTALL)
_EDITION_PATH = re.compile(r"^c/(\d{4}-\d{2}-\d{2})/?$")


@dataclass(frozen=True)
class Preview:
    title: str
    description: str
    url: str
    image: str
    image_alt: str


def edition_date(path: str) -> date | None:
    match = _EDITION_PATH.match(path)
    if not match:
        return None
    try:
        return dates.validate(match.group(1))
    except InvalidDateError:
        return None


async def _headlines(day: date, stored: FrontPage | None) -> list[str]:
    if stored is not None and stored.editorial is not None:
        return [h.title for h in stored.editorial.headlines]
    stored_editorial = await editorial.load_stored(day)
    return [h.title for h in stored_editorial.headlines] if stored_editorial else []


def _photo(stored: FrontPage | None) -> tuple[str, str] | None:
    if stored is None:
        return None
    by_id = {event.id: event for event in stored.events}
    ids = (
        [headline.event_id for headline in stored.editorial.headlines]
        if stored.editorial is not None
        else [event.id for event in stored.events[:3]]
    )
    for event_id in ids:
        event = by_id.get(event_id)
        if event is not None and event.image_url:
            return event.image_url, event.text[:120]
    return None


# Título, manchetes e foto usados na prévia do link compartilhado.
async def build_preview(day: date, base_url: str) -> Preview:
    long_date = dates.long_format(day)
    stored = await front_page.load(day)
    headlines, photo = await _headlines(day, stored), _photo(stored)
    if headlines:
        description = " · ".join(headlines)
        if len(description) > MAX_DESCRIPTION:
            description = description[: MAX_DESCRIPTION - 1].rsplit(" ", 1)[0] + "…"
    else:
        description = (
            f"As manchetes, o tempo, o dólar e o Brasil de {day.year} na capa de {long_date}."
        )
    image, image_alt = photo or (f"{base_url}{DEFAULT_IMAGE}", SITE_NAME)
    return Preview(
        title=f"Jornal de {long_date}",
        description=description,
        url=f"{base_url}/c/{day.isoformat()}",
        image=image,
        image_alt=image_alt,
    )


def home_preview(base_url: str) -> Preview:
    return Preview(
        title=SITE_NAME,
        description=DEFAULT_DESCRIPTION,
        url=f"{base_url}/",
        image=f"{base_url}{DEFAULT_IMAGE}",
        image_alt=SITE_NAME,
    )


def render_tags(preview: Preview) -> str:
    full_title = preview.title if preview.title == SITE_NAME else f"{preview.title} · {SITE_NAME}"
    title = escape(full_title)
    tags = [
        f"<title>{title}</title>",
        f'<meta name="description" content="{escape(preview.description)}" />',
        '<meta property="og:type" content="article" />',
        '<meta property="og:locale" content="pt_BR" />',
        f'<meta property="og:site_name" content="{escape(SITE_NAME)}" />',
        f'<meta property="og:title" content="{escape(preview.title)}" />',
        f'<meta property="og:description" content="{escape(preview.description)}" />',
        f'<meta property="og:url" content="{escape(preview.url)}" />',
        f'<meta property="og:image" content="{escape(preview.image)}" />',
        f'<meta property="og:image:alt" content="{escape(preview.image_alt)}" />',
        '<meta name="twitter:card" content="summary_large_image" />',
    ]
    return "<!-- og -->\n    " + "\n    ".join(tags) + "\n    <!-- /og -->"


def inject(index_html: str, preview: Preview) -> str:
    return _BLOCK.sub(lambda _: render_tags(preview), index_html, count=1)
