from __future__ import annotations

from datetime import datetime, timezone

from custom_components.transit_departures.api import StopSearchResult


def service_day_timestamp(year: int = 2026, month: int = 5, day: int = 22) -> int:
    """Return a deterministic UTC midnight epoch timestamp for service day."""
    return int(datetime(year, month, day, tzinfo=timezone.utc).timestamp())


def search_results() -> list[StopSearchResult]:
    return [
        StopSearchResult(stop_id="HSL:1040273", label="Helsinki Main"),
        StopSearchResult(stop_id="HSL:1041402", label="Kamppi"),
    ]


def graphql_stops_payload() -> list[dict]:
    service_day = service_day_timestamp()
    return [
        {
            "gtfsId": "HSL:1040273",
            "name": "Helsinki Main",
            "code": "H1243",
            "alerts": [
                {
                    "alertSeverityLevel": "INFO",
                    "alertHeaderText": "Minor delay",
                    "alertHeaderTextTranslations": [
                        {"language": "fi", "text": "Pieni viive"}
                    ],
                    "effectiveStartDate": "2026-05-22T06:00:00+00:00",
                    "effectiveEndDate": "2026-05-22T12:00:00+00:00",
                }
            ],
            "stoptimesForPatterns": [
                {
                    "pattern": {
                        "code": "550",
                        "headsign": "Itakeskus",
                        "route": {"shortName": "550", "longName": "Jokeri"},
                    },
                    "stoptimes": [
                        {
                            "serviceDay": service_day,
                            "scheduledDeparture": 8 * 3600,
                            "realtimeDeparture": 8 * 3600 + 120,
                            "realtimeState": "UPDATED",
                        },
                        {
                            "serviceDay": service_day,
                            "scheduledDeparture": 8 * 3600 + 600,
                            "realtimeDeparture": 8 * 3600 + 600,
                            "realtimeState": "SCHEDULED",
                        },
                    ],
                }
            ],
        }
    ]


def graphql_response(stops: list[dict] | None = None) -> dict:
    return {"data": {"stops": stops if stops is not None else graphql_stops_payload()}}
