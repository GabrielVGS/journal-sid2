from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.schemas import ApiError, Source


class InvalidInputError(Exception):
    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class InvalidDateError(InvalidInputError):
    pass


# Fonte externa fora do ar ou com resposta inesperada.
class SourceUnavailableError(Exception):
    def __init__(self, source: Source, reason: str) -> None:
        super().__init__(f"{source}: {reason}")
        self.source: Source = source
        self.reason = reason


class RateLimitError(Exception):
    pass


def _error(status: int, detail: str, source: Source | None = None) -> JSONResponse:
    return JSONResponse(
        status_code=status, content=ApiError(detail=detail, source=source).model_dump()
    )


# Converte as exceções em respostas JSON com mensagem em português.
def register_handlers(app: FastAPI) -> None:

    @app.exception_handler(InvalidInputError)
    async def _invalid_input(_: Request, exc: InvalidInputError) -> JSONResponse:
        return _error(422, exc.detail)

    @app.exception_handler(RequestValidationError)
    async def _invalid_request(_: Request, __: RequestValidationError) -> JSONResponse:
        return _error(422, "Pedido inválido. Confira a data no formato AAAA-MM-DD.")

    @app.exception_handler(SourceUnavailableError)
    async def _source_unavailable(_: Request, exc: SourceUnavailableError) -> JSONResponse:
        return _error(503, "Correspondente sem sinal. Tente de novo em instantes.", exc.source)

    @app.exception_handler(RateLimitError)
    async def _rate_limited(_: Request, __: RateLimitError) -> JSONResponse:
        return _error(429, "Muitas capas novas em pouco tempo. Aguarde alguns minutos.")
