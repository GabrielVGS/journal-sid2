from psycopg_pool import AsyncConnectionPool

from app.config import get_settings

# Tabelas: cache das APIs externas, capas prontas e cota diária da Alpha Vantage.
SCHEMA = """
CREATE TABLE IF NOT EXISTS cache (
    key        TEXT PRIMARY KEY,
    value      JSONB NOT NULL,
    expires_at DOUBLE PRECISION NOT NULL
);
CREATE TABLE IF NOT EXISTS front_pages (
    date       DATE PRIMARY KEY,
    page       JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL
);
CREATE TABLE IF NOT EXISTS av_quota (
    day        DATE PRIMARY KEY,
    calls      INTEGER NOT NULL
);
"""

_pool: AsyncConnectionPool | None = None


async def open_pool(url: str | None = None) -> AsyncConnectionPool:
    global _pool
    await close_pool()
    url = url or get_settings().database_url
    if not url:
        raise RuntimeError("DATABASE_URL is not set (see .env.example).")
    pool = AsyncConnectionPool(
        url,
        min_size=1,
        max_size=5,
        # O pooler do Neon (PgBouncer) não aceita prepared statements.
        kwargs={"prepare_threshold": None, "autocommit": True},
        # O Neon encerra conexões ociosas; testa cada uma antes de usar.
        check=AsyncConnectionPool.check_connection,
        max_idle=120,
        open=False,
    )
    await pool.open(wait=True)
    async with pool.connection() as connection:
        await connection.execute(SCHEMA)
    _pool = pool
    return pool


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


def get_pool() -> AsyncConnectionPool:
    if _pool is None:
        raise RuntimeError("Database pool is not open; call open_pool() first.")
    return _pool
