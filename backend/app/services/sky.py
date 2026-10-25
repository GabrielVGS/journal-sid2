import asyncio
import math
import re
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta

import astronomy

from app.core import dates
from app.core.cache import DAY, cached
from app.core.errors import SourceUnavailableError
from app.core.http import get_json
from app.schemas import Sky, SkyObject, SkyTip
from app.services import moon

HORIZONS_URL = "https://ssd.jpl.nasa.gov/api/horizons.api"
REFERENCE_TIME = time(21, 0)
LATITUDE, LONGITUDE, ALTITUDE_KM = -15.78, -47.93, 1.1

BODIES: dict[str, str] = {
    "301": "Lua",
    "199": "Mercúrio",
    "299": "Vênus",
    "499": "Marte",
    "599": "Júpiter",
    "699": "Saturno",
}

_NUMBER = re.compile(r"^-?\d+(?:\.\d+)?$")


@dataclass(frozen=True)
class Star:
    name: str
    ra_hours: float
    dec_degrees: float
    magnitude: float


STARS = [
    Star("Sírius", 6.7525, -16.716, -1.46),
    Star("Canopus", 6.3992, -52.696, -0.74),
    Star("Alfa do Centauro", 14.6600, -60.834, -0.27),
    Star("Arcturus", 14.2610, 19.182, -0.05),
    Star("Vega", 18.6156, 38.784, 0.03),
    Star("Capela", 5.2782, 45.998, 0.08),
    Star("Rigel", 5.2423, -8.202, 0.13),
    Star("Prócion", 7.6550, 5.225, 0.34),
    Star("Achernar", 1.6286, -57.237, 0.46),
    Star("Betelgeuse", 5.9195, 7.407, 0.50),
    Star("Hadar", 14.0637, -60.373, 0.61),
    Star("Altair", 19.8464, 8.868, 0.76),
    Star("Acrux", 12.4433, -63.099, 0.77),
    Star("Aldebarã", 4.5987, 16.509, 0.86),
    Star("Antares", 16.4901, -26.432, 0.96),
    Star("Espiga", 13.4199, -11.161, 0.97),
    Star("Pólux", 7.7553, 28.026, 1.14),
    Star("Fomalhaut", 22.9608, -29.622, 1.16),
    Star("Deneb", 20.6905, 45.280, 1.25),
    Star("Mimosa", 12.7953, -59.689, 1.25),
    Star("Régulo", 10.1395, 11.967, 1.35),
    Star("Gacrux", 12.5194, -57.113, 1.64),
    Star("Pálida", 12.2524, -58.749, 2.79),
    Star("Intrometida", 12.3560, -60.401, 3.59),
    Star("Bellatrix", 5.4189, 6.350, 1.64),
    Star("Alnitak", 5.6793, -1.943, 1.77),
    Star("Alnilam", 5.6036, -1.202, 1.69),
    Star("Mintaka", 5.5334, -0.299, 2.23),
    Star("Saiph", 5.7959, -9.670, 2.09),
    Star("Shaula", 17.5601, -37.104, 1.62),
    Star("Sargas", 17.6220, -42.998, 1.86),
    Star("Dschubba", 16.0056, -22.622, 2.29),
    Star("Acrab", 16.0906, -19.806, 2.62),
    Star("Tau Escorpião", 16.5980, -28.216, 2.82),
    Star("Larawag", 16.8361, -34.293, 2.29),
    Star("Mu Escorpião", 16.8645, -38.047, 3.00),
    Star("Kappa Escorpião", 17.7081, -39.030, 2.39),
]

CONSTELLATIONS: list[tuple[str, list[tuple[str, str]]]] = [
    ("Cruzeiro do Sul", [("Acrux", "Gacrux"), ("Mimosa", "Pálida")]),
    (
        "Órion",
        [
            ("Betelgeuse", "Bellatrix"),
            ("Betelgeuse", "Alnitak"),
            ("Bellatrix", "Mintaka"),
            ("Alnitak", "Alnilam"),
            ("Alnilam", "Mintaka"),
            ("Alnitak", "Saiph"),
            ("Mintaka", "Rigel"),
        ],
    ),
    (
        "Escorpião",
        [
            ("Acrab", "Dschubba"),
            ("Dschubba", "Antares"),
            ("Antares", "Tau Escorpião"),
            ("Tau Escorpião", "Larawag"),
            ("Larawag", "Mu Escorpião"),
            ("Mu Escorpião", "Sargas"),
            ("Sargas", "Kappa Escorpião"),
            ("Kappa Escorpião", "Shaula"),
        ],
    ),
]

_DIRECTIONS = ["norte", "nordeste", "leste", "sudeste", "sul", "sudoeste", "oeste", "noroeste"]


def direction(azimuth: float) -> str:
    return _DIRECTIONS[round(azimuth / 45) % 8]


def height(altitude: float, feminine: bool = False) -> str:
    if altitude < 20:
        return "baixa" if feminine else "baixo"
    if altitude < 55:
        return "a meia altura"
    if altitude < 80:
        return "alta" if feminine else "alto"
    return "quase sobre a cabeça"


def where(o: SkyObject, feminine: bool = False) -> str:
    how_high = height(o.altitude, feminine)
    return how_high if o.altitude >= 80 else f"{how_high} no {direction(o.azimuth)}"


def moon_title(phase: str) -> str:
    return f"Lua em {phase.lower()}" if phase.startswith("Quarto") else f"Lua {phase.lower()}"


def separation(a: SkyObject, b: SkyObject) -> float:
    alt1, alt2 = math.radians(a.altitude), math.radians(b.altitude)
    daz = math.radians(a.azimuth - b.azimuth)
    cosine = math.sin(alt1) * math.sin(alt2) + math.cos(alt1) * math.cos(alt2) * math.cos(daz)
    return math.degrees(math.acos(max(-1.0, min(1.0, cosine))))


def night_of(day: date) -> datetime:
    return datetime.combine(day, REFERENCE_TIME, dates.TIMEZONE).astimezone(UTC)


@cached("horizons", ttl=365 * DAY)
async def fetch_horizons_raw(body: str, moment: str) -> str:
    start = datetime.fromisoformat(moment)
    params = {
        "format": "json",
        "COMMAND": f"'{body}'",
        "EPHEM_TYPE": "'OBSERVER'",
        "CENTER": "'coord@399'",
        "COORD_TYPE": "'GEODETIC'",
        "SITE_COORD": f"'{LONGITUDE},{LATITUDE},{ALTITUDE_KM}'",
        "START_TIME": f"'{start:%Y-%m-%d %H:%M}'",
        "STOP_TIME": f"'{start + timedelta(minutes=1):%Y-%m-%d %H:%M}'",
        "STEP_SIZE": "'1m'",
        "QUANTITIES": "'4,9'",
    }
    payload = await get_json("nasa", HORIZONS_URL, params=params)
    result = payload.get("result") if isinstance(payload, dict) else None
    if not isinstance(result, str) or "$$SOE" not in result:
        raise SourceUnavailableError("nasa", f"Horizons: no ephemeris for {body}")
    return result


def parse_horizons(result: str) -> tuple[float, float, float | None]:
    row = result.split("$$SOE", 1)[1].split("$$EOE", 1)[0].strip().splitlines()[0]
    numbers = [float(token) for token in row.split()[2:] if _NUMBER.match(token)]
    if len(numbers) < 2:
        raise SourceUnavailableError("nasa", "Horizons: unexpected row")
    return numbers[0], numbers[1], numbers[2] if len(numbers) > 2 else None


def place_stars(moment: datetime) -> list[SkyObject]:
    observer = astronomy.Observer(LATITUDE, LONGITUDE, ALTITUDE_KM * 1000)
    at = astronomy.Time.Make(
        moment.year, moment.month, moment.day, moment.hour, moment.minute, moment.second
    )
    stars = []
    for star in STARS:
        horizon = astronomy.Horizon(
            at, observer, star.ra_hours, star.dec_degrees, astronomy.Refraction.Normal
        )
        stars.append(
            SkyObject(
                name=star.name,
                kind="star",
                azimuth=round(horizon.azimuth, 2),
                altitude=round(horizon.altitude, 2),
                magnitude=star.magnitude,
            )
        )
    return stars


PAIRED_DEGREES = 10
NEAR_STAR_DEGREES = 8
SYMBOLS = {"Mercúrio": "☿", "Vênus": "♀", "Marte": "♂", "Júpiter": "♃", "Saturno": "♄"}


def guide(bodies: list[SkyObject], stars: list[SkyObject], moon_phase: str) -> list[SkyTip]:
    up = [b for b in bodies if b.altitude > 0]
    planets = sorted(
        (b for b in up if b.kind == "planet"),
        key=lambda b: b.magnitude if b.magnitude is not None else 9,
    )
    bright = [s for s in stars if s.altitude > 0 and (s.magnitude or 9) < 1.5]
    tips = []
    moon = next((b for b in up if b.kind == "moon"), None)
    if moon is not None:
        detail = where(moon, feminine=True)
        beside = [p.name for p in planets if separation(p, moon) <= PAIRED_DEGREES]
        if beside:
            detail += ", ao lado de " + " e ".join(beside)
        tips.append(SkyTip(symbol="☾", title=moon_title(moon_phase), detail=detail + "."))
    for planet in planets:
        detail = where(planet)
        star = min(bright, key=lambda s: separation(s, planet), default=None)
        if star is not None and separation(star, planet) <= NEAR_STAR_DEGREES:
            detail += f", perto de {star.name}"
        tips.append(
            SkyTip(symbol=SYMBOLS.get(planet.name, "•"), title=planet.name, detail=detail + ".")
        )
    crux = next((s for s in stars if s.name == "Acrux" and s.altitude > 0), None)
    if crux is not None:
        tips.append(
            SkyTip(
                symbol="✢",
                title="Cruzeiro do Sul",
                detail=f"{where(crux)}.",
            )
        )
    return tips


async def get_sky(day: date) -> Sky:
    moment = night_of(day)
    stamp = f"{moment:%Y-%m-%d %H:%M}"
    results = await asyncio.gather(
        *(fetch_horizons_raw(body, stamp) for body in BODIES), return_exceptions=True
    )
    if all(isinstance(result, BaseException) for result in results):
        raise SourceUnavailableError("nasa", "Horizons did not answer")
    bodies = []
    for (body, name), result in zip(BODIES.items(), results, strict=True):
        if isinstance(result, BaseException):
            continue
        azimuth, altitude, magnitude = parse_horizons(result)
        bodies.append(
            SkyObject(
                name=name,
                kind="moon" if body == "301" else "planet",
                azimuth=round(azimuth, 2),
                altitude=round(altitude, 2),
                magnitude=magnitude,
            )
        )
    stars = place_stars(moment)
    return Sky(
        date=day,
        objects=[*stars, *bodies],
        constellations=[
            {"name": name, "lines": [list(pair) for pair in pairs]}
            for name, pairs in CONSTELLATIONS
        ],
        guide=guide(bodies, stars, moon.moon_on(day).phase),
    )
