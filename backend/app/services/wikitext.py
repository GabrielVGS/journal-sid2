import re
from urllib.parse import quote

import mwparserfromhell

from app.core.cache import DAY, cached
from app.core.errors import SourceUnavailableError
from app.core.http import get_json

PARSE_URL = "https://{lang}.wikipedia.org/w/api.php"
ARTICLE_URL = "https://{lang}.wikipedia.org/wiki/"

# Link de data em wikitext: [[20 de julho]], [[1º de julho]] ou [[1 de julho|1º]].
# Grupos: dia e nome do mês.
_DATE_LINK = re.compile(r"\[\[(\d{1,2})(?:º|\.º)? de ([a-zç]+)(?:\|[^\]]*)?\]\]", re.IGNORECASE)
_NAMESPACES = ("ficheiro:", "arquivo:", "imagem:", "file:", "image:", "categoria:", "category:")


# Texto bruto (wikitext) de uma página; página inexistente devolve vazio.
@cached("wikipedia:wikitext", ttl=30 * DAY)
async def fetch_wikitext(page: str, lang: str = "pt") -> str:
    params = {
        "action": "parse",
        "page": page,
        "prop": "wikitext",
        "format": "json",
        "formatversion": 2,
        "redirects": 1,
    }
    body = await get_json("wikipedia", PARSE_URL.format(lang=lang), params=params)
    if "error" in body:
        if body["error"].get("code") == "missingtitle":
            return ""
        raise SourceUnavailableError("wikipedia", body["error"].get("info", "parse error"))
    text: str = body["parse"]["wikitext"]
    return text


def article_url(title: str, lang: str = "pt") -> str:
    return ARTICLE_URL.format(lang=lang) + quote(title.replace(" ", "_"))


# Remove a marcação e devolve o texto limpo e os artigos citados.
def clean_wikitext(fragment: str) -> tuple[str, tuple[str, ...]]:
    code = mwparserfromhell.parse(fragment)
    for external in code.filter_external_links():
        code.remove(external)
    for link in code.filter_wikilinks():
        if str(link.title).strip().lower().startswith(_NAMESPACES):
            code.remove(link)
    titles = [str(link.title).strip() for link in code.filter_wikilinks()]
    links = tuple(
        dict.fromkeys(
            title
            for title in titles
            if not _DATE_LINK.fullmatch(f"[[{title}]]") and not title.isdigit()
        )
    )
    # Junta espaços e quebras de linha num espaço só e tira pontuação das pontas.
    text = re.sub(r"\s+", " ", code.strip_code()).strip(" .;-–")
    return text[:1].upper() + text[1:], links
