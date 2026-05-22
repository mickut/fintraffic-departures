from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class AlertInfo:
    severity: str | None
    header: str | None
    translations: dict[str, str]
    effective_start: datetime | None
    effective_end: datetime | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "severity": self.severity,
            "header": self.header,
            "translations": self.translations,
            "effective_start": self.effective_start.isoformat() if self.effective_start else None,
            "effective_end": self.effective_end.isoformat() if self.effective_end else None,
        }


@dataclass(frozen=True, slots=True)
class DepartureInfo:
    stop_id: str
    stop_name: str
    pattern_code: str
    headsign: str | None
    route_short_name: str | None
    route_long_name: str | None
    scheduled_datetime: datetime
    departure_datetime: datetime
    realtime_state: str | None
    delay_minutes: int

    @property
    def route_label(self) -> str:
        return self.route_short_name or self.route_long_name or self.pattern_code

    def as_dict(self) -> dict[str, Any]:
        return {
            "stop_id": self.stop_id,
            "stop_name": self.stop_name,
            "pattern_code": self.pattern_code,
            "headsign": self.headsign,
            "route_short_name": self.route_short_name,
            "route_long_name": self.route_long_name,
            "route_label": self.route_label,
            "scheduled_datetime": self.scheduled_datetime.isoformat(),
            "departure_datetime": self.departure_datetime.isoformat(),
            "realtime_state": self.realtime_state,
            "delay_minutes": self.delay_minutes,
        }


@dataclass(frozen=True, slots=True)
class StopData:
    stop_id: str
    stop_name: str
    stop_code: str | None
    departures: tuple[DepartureInfo, ...]
    alerts: tuple[AlertInfo, ...]
