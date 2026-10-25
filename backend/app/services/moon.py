from datetime import UTC, date, datetime, time

import astronomy

from app.core import dates
from app.schemas import Moon, MoonPhaseDate

REFERENCE_TIME = time(21, 0)
NEXT_PHASES = 2

MAIN_PHASES = ["Nova", "Quarto crescente", "Cheia", "Quarto minguante"]
BETWEEN_PHASES = ["Crescente", "Crescente gibosa", "Minguante gibosa", "Minguante"]


def _astro_time(moment: datetime) -> astronomy.Time:
    utc = moment.astimezone(UTC)
    return astronomy.Time.Make(
        utc.year, utc.month, utc.day, utc.hour, utc.minute, utc.second + utc.microsecond / 1e6
    )


def _local_date(moment: astronomy.Time) -> date:
    utc = datetime.fromisoformat(str(moment).replace("Z", "+00:00"))
    return utc.astimezone(dates.TIMEZONE).date()


def moon_on(day: date) -> Moon:
    night = _astro_time(datetime.combine(day, REFERENCE_TIME, dates.TIMEZONE))
    angle = astronomy.MoonPhase(night)
    illumination = astronomy.Illumination(astronomy.Body.Moon, night).phase_fraction

    quarter = astronomy.SearchMoonQuarter(
        _astro_time(datetime.combine(day, time(0, 0), dates.TIMEZONE))
    )
    name = BETWEEN_PHASES[int(angle // 90) % 4]
    upcoming: list[MoonPhaseDate] = []
    while len(upcoming) < NEXT_PHASES:
        when = _local_date(quarter.time)
        if when == day:
            name = MAIN_PHASES[quarter.quarter]
        else:
            upcoming.append(MoonPhaseDate(phase=MAIN_PHASES[quarter.quarter], date=when))
        quarter = astronomy.NextMoonQuarter(quarter)

    return Moon(
        date=day,
        phase=name,
        phase_angle=round(angle, 2),
        illumination=round(illumination, 4),
        waxing=angle < 180,
        next_phases=upcoming,
    )
