"""Day 5 timezone and roll-window helpers.

The module labels official schedule windows; it does not infer live exchange state
or create executable trading signals.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo


ET = ZoneInfo("America/New_York")


@dataclass(frozen=True)
class RollEvent:
    market: str
    local_date: date
    local_time: time
    front_month_percent: int
    next_month_percent: int

    def local_datetime(self) -> datetime:
        return datetime.combine(self.local_date, self.local_time, tzinfo=ET)

    def utc_datetime(self) -> datetime:
        return self.local_datetime().astimezone(timezone.utc)


def et_to_utc(local_date: date, hour: int, minute: int) -> datetime:
    """Convert an official ET schedule to UTC while respecting DST."""
    return datetime.combine(local_date, time(hour, minute), tzinfo=ET).astimezone(timezone.utc)


def roll_stage(front_month_percent: int) -> str:
    stages = {
        100: "pre_roll",
        80: "day_1",
        60: "day_2",
        40: "day_3",
        20: "day_4",
        0: "post_roll",
    }
    try:
        return stages[front_month_percent]
    except KeyError as exc:
        raise ValueError("front_month_percent must be one of 100, 80, 60, 40, 20, 0") from exc


def is_in_window(local_time: time, start: time, end: time) -> bool:
    """Return whether a same-day half-open window contains local_time."""
    return start <= local_time < end


def main() -> None:
    event_date = date(2026, 8, 7)
    for market, hour, minute in (("WTI", 17, 30), ("BRENTOIL", 19, 0)):
        utc_dt = et_to_utc(event_date, hour, minute)
        print(f"{market}: {event_date} {hour:02d}:{minute:02d} ET -> {utc_dt.isoformat()}")
    print("WTI stage 80:", roll_stage(80))
    print("BRENTOIL stage 20:", roll_stage(20))
    print("WTI close contains 17:30:", is_in_window(time(17, 30), time(17), time(18)))
    print("BRENTOIL close contains 19:00:", is_in_window(time(19), time(18), time(20)))


if __name__ == "__main__":
    main()
