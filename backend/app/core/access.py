import base64
import binascii
import re
import secrets
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response

from app.config import get_settings

# Rotas liberadas sem senha (monitoramento do Render).
OPEN_PATHS = frozenset({"/api/health"})
# Robôs de prévia de link (WhatsApp etc.) podem ler as páginas sem senha.
PREVIEW_BOTS = re.compile(
    r"WhatsApp|facebookexternalhit|Facebot|Twitterbot|TelegramBot|Slackbot|Discordbot|LinkedInBot",
    re.IGNORECASE,
)
CHALLENGE = 'Basic realm="O Jornal do Dia", charset="UTF-8"'


# HTTP Basic: só a senha é conferida; o usuário pode ser qualquer um.
def password_matches(header: str | None, password: str) -> bool:
    if not header or not header.lower().startswith("basic "):
        return False
    try:
        decoded = base64.b64decode(header[6:].strip(), validate=True).decode("utf-8")
    except (binascii.Error, UnicodeDecodeError):
        return False
    _, _, given = decoded.partition(":")
    return secrets.compare_digest(given.encode(), password.encode())


def is_open(request: Request) -> bool:
    path = request.url.path
    if path in OPEN_PATHS:
        return True
    is_page = not path.startswith("/api/")
    return is_page and bool(PREVIEW_BOTS.search(request.headers.get("user-agent", "")))


# Middleware que pede a senha em todas as rotas, se SITE_PASSWORD estiver definida.
def install(app: FastAPI) -> None:

    @app.middleware("http")
    async def require_password(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        password = get_settings().site_password
        if not password or is_open(request):
            return await call_next(request)
        if password_matches(request.headers.get("authorization"), password):
            return await call_next(request)
        return Response(
            "Senha necessária.",
            status_code=401,
            headers={"WWW-Authenticate": CHALLENGE},
            media_type="text/plain; charset=utf-8",
        )
