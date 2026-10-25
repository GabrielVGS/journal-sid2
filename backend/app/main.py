from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, Response
from fastapi.staticfiles import StaticFiles

from app.api import front_page, health, sections
from app.config import ROOT_DIR
from app.core import access
from app.core.db import close_pool, open_pool
from app.core.errors import register_handlers
from app.core.http import close_client
from app.domain import share

DIST_DIR = ROOT_DIR / "frontend" / "dist"


# Abre o pool do banco ao iniciar e fecha as conexões ao desligar.
@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    await open_pool()
    yield
    await close_client()
    await close_pool()


app = FastAPI(
    title="O Jornal do Dia",
    version="0.1.0",
    lifespan=lifespan,
    separate_input_output_schemas=False,
)
register_handlers(app)
access.install(app)
app.include_router(front_page.router)
app.include_router(sections.router)
app.include_router(health.router)


# Em produção o próprio FastAPI serve o frontend compilado (SPA).
if DIST_DIR.is_dir():
    app.mount("/assets", StaticFiles(directory=DIST_DIR / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    async def spa(path: str, request: Request) -> Response:
        if path.startswith("api/"):
            raise HTTPException(status_code=404)
        file = DIST_DIR / path
        if path and file.is_file():
            return FileResponse(file)
        # Páginas de capa recebem as tags Open Graph para a prévia do link.
        day = share.edition_date(path)
        base_url = str(request.base_url).rstrip("/")
        if day is not None:
            preview = await share.build_preview(day, base_url)
        elif not path:
            preview = share.home_preview(base_url)
        else:
            return FileResponse(DIST_DIR / "index.html")
        html = share.inject((DIST_DIR / "index.html").read_text(encoding="utf-8"), preview)
        return HTMLResponse(html)
