from datetime import date

from app.core.dates import long_format
from app.schemas import Event, Exchange, Indicator

# from app.services import moon  (desativado)

# Instruções do editorial: escrever como no próprio dia e só com os fatos enviados.
SYSTEM = """Você é o editor-chefe de um jornal brasileiro impresso publicado em {date}.
Escreva como se estivesse nesse exato dia:
- não mencione nada posterior a {date} nem o presente;
- use SOMENTE os fatos fornecidos; não invente nomes, números, citações ou eventos;
- português do Brasil, tom jornalístico da época, sem exageros.

Responda com:
- "headlines": de 1 a 3 manchetes. Cada uma com "title" (até 90 caracteres, impactante),
  "subtitle" (uma frase) e "event_id" (o id EXATO de um dos fatos, ex.: "e1").
  A primeira manchete é a mais importante; prefira fatos "neste dia".
  Manchetes só citam fatos "neste dia" ou "neste mês" (se houver menos de 3, faça menos);
  efemérides só viram manchete quando não há nenhum outro fato.
  Nunca escreva o id do evento dentro do título ou do subtítulo.
- "title": título do editorial (até 80 caracteres).
- "body": editorial de 150 a 250 palavras, em 2 a 4 parágrafos separados por uma linha em branco,
  comentando os fatos do dia e o retrato do Brasil da época.
  Efemérides entram como lembrança do passado ("há N anos, ...")."""


def _format_number(value: float) -> str:
    return f"{value:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")


def build_editorial_prompt(
    day: date, events: list[Event], indicators: list[Indicator], exchange: Exchange | None
) -> tuple[str, str]:
    lines = ["FATOS (use o id para citar):"]
    for event in events:
        when = long_format(event.date) if event.date else str(event.year or "")
        kind = {"day": "neste dia", "month": "neste mês", "on_this_day": "efeméride"}[event.layer]
        lines.append(f"- {event.id} [{kind}, {when}]: {event.text}")
    if indicators:
        lines.append("\nRETRATO DO BRASIL (dados da época):")
        lines += [
            f"- {i.name}: {_format_number(i.then_value)} {i.unit} ({i.then_year})"
            for i in indicators
        ]
    if exchange:
        lines.append(
            f"\nMOEDA EM CIRCULAÇÃO: {exchange.currency.name} ({exchange.currency.symbol})"
        )
        if exchange.usd_then:
            period = (
                f"média anual de {exchange.usd_then_period}"
                if exchange.usd_then_source == "worldbank"
                else f"fechamento do mês {exchange.usd_then_period}"
            )
            lines.append(
                f"- dólar ({period}, não é a cotação do dia): "
                f"{exchange.currency.symbol} {_format_number(exchange.usd_then)}"
            )
    # Desativado: Lua
    # night = moon.moon_on(day)
    # lines.append(
    #     f"\nLUA NAQUELA NOITE: {night.phase}, {round(night.illumination * 100)}% iluminada"
    # )
    return SYSTEM.format(date=long_format(day)), "\n".join(lines)
