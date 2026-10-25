import time
from collections import defaultdict, deque

from fastapi import Request

from app.core.errors import RateLimitError

# Limite por IP para capas novas (capas já salvas não contam).
MAX_NEW_PAGES = 10
WINDOW_SECONDS = 3600

_hits: defaultdict[str, deque[float]] = defaultdict(deque)


# Janela deslizante: descarta acessos com mais de uma hora e conta o resto.
def check_new_page(request: Request) -> None:
    ip = request.client.host if request.client else "unknown"
    now = time.monotonic()
    hits = _hits[ip]
    while hits and hits[0] <= now - WINDOW_SECONDS:
        hits.popleft()
    if len(hits) >= MAX_NEW_PAGES:
        raise RateLimitError
    hits.append(now)


def reset() -> None:
    _hits.clear()
