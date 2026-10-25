import html
import re

# Qualquer tag HTML, como <b> ou </a>.
_TAG = re.compile(r"<[^>]+>")
# Sequência de espaços, tabs ou quebras de linha.
_SPACES = re.compile(r"\s+")


def strip_html(value: str) -> str:
    return _SPACES.sub(" ", html.unescape(_TAG.sub(" ", value))).strip()


def truncate(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    return value[:limit].rsplit(" ", 1)[0].rstrip(".,;:") + "…"
