from datetime import date
from typing import Annotated

from fastapi import Depends, Query

from app.core import dates
from app.schemas import ApiError


def _valid_date(
    date_: Annotated[
        str,
        Query(
            alias="date",
            description="Date `YYYY-MM-DD`, from 1900-01-01 to yesterday (São Paulo time).",
            examples=["1969-07-20"],
        ),
    ],
) -> date:
    return dates.validate(date_)


# Parâmetro ?date= já validado, reutilizado em todas as rotas.
ValidDate = Annotated[date, Depends(_valid_date)]

ERROR_RESPONSES: dict[int | str, dict[str, object]] = {
    422: {"model": ApiError, "description": "Invalid date or request."},
    503: {"model": ApiError, "description": "External source unavailable."},
}
