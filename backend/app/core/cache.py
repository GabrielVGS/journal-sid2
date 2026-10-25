import functools
import hashlib
import json
import time
from collections.abc import Awaitable, Callable
from typing import Any

from psycopg.types.json import Jsonb

from app.core.db import get_pool

HOUR = 3600
DAY = 24 * HOUR
MAX_READABLE_KEY = 200

now: Callable[[], float] = time.time


# Chave = prefixo + argumentos; chaves longas viram hash para caber no índice.
def make_key(prefix: str, args: tuple[Any, ...], kwargs: dict[str, Any]) -> str:
    arguments = json.dumps([args, kwargs], default=str, sort_keys=True, ensure_ascii=False)
    if len(prefix) + len(arguments) < MAX_READABLE_KEY:
        return f"{prefix}:{arguments}"
    return f"{prefix}:sha256:{hashlib.sha256(arguments.encode()).hexdigest()}"


async def read(key: str) -> Any | None:
    async with get_pool().connection() as connection:
        cursor = await connection.execute(
            "SELECT value FROM cache WHERE key = %s AND expires_at >= %s", (key, now())
        )
        row = await cursor.fetchone()
    return row[0] if row else None


async def write(key: str, value: Any, ttl: float) -> None:
    async with get_pool().connection() as connection:
        await connection.execute(
            "INSERT INTO cache (key, value, expires_at) VALUES (%s, %s, %s) "
            "ON CONFLICT (key) DO UPDATE "
            "SET value = EXCLUDED.value, expires_at = EXCLUDED.expires_at",
            (key, Jsonb(value), now() + ttl),
        )


# Decorator: guarda no banco o retorno da função por `ttl` segundos.
# Se a função levantar erro, nada é guardado.
def cached[**P, R](
    prefix: str, ttl: float
) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:

    def decorator(func: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            key = make_key(prefix, args, kwargs)
            stored = await read(key)
            if stored is not None:
                return stored  # type: ignore[no-any-return]
            value = await func(*args, **kwargs)
            await write(key, value, ttl)
            return value

        return wrapper

    return decorator
