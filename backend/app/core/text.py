import html
import re

_TAG = re.compile(r"<[^>]+>")
_SPACES = re.compile(r"\s+")


def strip_html(value: str) -> str:
    return _SPACES.sub(" ", html.unescape(_TAG.sub(" ", value))).strip()


def truncate(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    return value[:limit].rsplit(" ", 1)[0].rstrip(".,;:") + "…"
