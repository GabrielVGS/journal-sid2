from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from app.core.errors import InvalidDateError

TIMEZONE = ZoneInfo("America/Sao_Paulo")
MIN_DATE = date(1900, 1, 1)

MONTH_NAMES = [
    "janeiro",
    "fevereiro",
    "março",
    "abril",
    "maio",
    "junho",
    "julho",
    "agosto",
    "setembro",
    "outubro",
    "novembro",
    "dezembro",
]


def today() -> date:
    return datetime.now(TIMEZONE).date()


def yesterday() -> date:
    return today() - timedelta(days=1)


# Aceita datas de 01/01/1900 até ontem, no fuso de São Paulo.
def validate(value: str | date) -> date:
    if isinstance(value, str):
        try:
            value = date.fromisoformat(value)
        except ValueError:
            raise InvalidDateError("Data inválida. Use o formato AAAA-MM-DD.") from None
    if value < MIN_DATE:
        raise InvalidDateError("Nosso arquivo começa em 1º de janeiro de 1900.")
    if value > yesterday():
        raise InvalidDateError("Essa edição ainda não foi impressa. Escolha uma data até ontem.")
    return value


def issue_number(day: date) -> int:
    return (day - MIN_DATE).days + 1


def long_format(day: date) -> str:
    day_text = "1º" if day.day == 1 else str(day.day)
    return f"{day_text} de {MONTH_NAMES[day.month - 1]} de {day.year}"
