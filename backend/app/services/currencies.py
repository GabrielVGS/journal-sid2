from dataclasses import dataclass
from datetime import date

from app.schemas import Currency


@dataclass(frozen=True)
class CurrencyPeriod:
    name: str
    symbol: str
    start: date
    end: date | None
    per_real: float

    def to_schema(self) -> Currency:
        return Currency(name=self.name, symbol=self.symbol, start=self.start, end=self.end)


# Moedas do Brasil e quantas unidades de cada uma equivalem a 1 real.
CURRENCIES = [
    CurrencyPeriod("Réis", "Rs", date(1833, 10, 8), date(1942, 10, 31), 2.75e18),
    CurrencyPeriod("Cruzeiro", "Cr$", date(1942, 11, 1), date(1967, 2, 12), 2.75e15),
    CurrencyPeriod("Cruzeiro Novo", "NCr$", date(1967, 2, 13), date(1970, 5, 14), 2.75e12),
    CurrencyPeriod("Cruzeiro", "Cr$", date(1970, 5, 15), date(1986, 2, 27), 2.75e12),
    CurrencyPeriod("Cruzado", "Cz$", date(1986, 2, 28), date(1989, 1, 15), 2.75e9),
    CurrencyPeriod("Cruzado Novo", "NCz$", date(1989, 1, 16), date(1990, 3, 15), 2.75e6),
    CurrencyPeriod("Cruzeiro", "Cr$", date(1990, 3, 16), date(1993, 7, 31), 2.75e6),
    CurrencyPeriod("Cruzeiro Real", "CR$", date(1993, 8, 1), date(1994, 6, 30), 2750),
    CurrencyPeriod("Real", "R$", date(1994, 7, 1), None, 1),
]


def currency_on(day: date) -> CurrencyPeriod:
    for period in reversed(CURRENCIES):
        if day >= period.start:
            return period
    return CURRENCIES[0]
