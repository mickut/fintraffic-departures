from __future__ import annotations

import json
from datetime import timedelta
from pathlib import Path

DOMAIN = "fintraffic_departures"

CONF_STOP_IDS = "stop_ids"
CONF_NUMBER_OF_DEPARTURES = "number_of_departures"
CONF_CUTOFF_MINUTES = "cutoff_minutes"
CONF_UPDATE_INTERVAL_MINUTES = "update_interval_minutes"

DEFAULT_NUMBER_OF_DEPARTURES = 4
DEFAULT_CUTOFF_MINUTES = 0
DEFAULT_UPDATE_INTERVAL_MINUTES = 15
COORDINATOR_UPDATE_INTERVAL = timedelta(minutes=1)

GRAPHQL_URL = "https://matkamonitori.digitransit.fi/api/graphql"
GRAPHQL_ENDPOINT_VALUE = "routing/v2/finland/gtfs/v1"
GRAPHQL_USER_HEADER = "Digitraffic-User"

ATTR_PRIMARY_DEPARTURE = "primary_departure"
ATTR_NEXT_DEPARTURES = "next_departures"
ATTR_ALERTS = "alerts"
ATTR_STOP_ID = "stop_id"
ATTR_STOP_NAME = "stop_name"


def _load_integration_version() -> str:
  manifest_path = Path(__file__).with_name("manifest.json")
  try:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
  except (OSError, json.JSONDecodeError):
    return "0.0.0"

  version = manifest.get("version")
  if isinstance(version, str) and version:
    return version
  return "0.0.0"


DIGITRAFFIC_USER = f"mickut/HACS-FintrafficDepartures {_load_integration_version()}"

QUERY_GET_DEPARTURES = """
query GetDeparturesForStops($ids: [String!]!, $numberOfDepartures: Int!) {
  stops: stops(ids: $ids) {
    gtfsId
    name
    alerts {
      alertSeverityLevel
      alertHeaderText
      alertHeaderTextTranslations {
        text
        language
      }
      effectiveStartDate
      effectiveEndDate
    }
    stoptimesForPatterns(numberOfDepartures: $numberOfDepartures, omitCanceled: false) {
      pattern {
        code
        headsign
        route {
          shortName
          longName
        }
      }
      stoptimes {
        serviceDay
        scheduledDeparture
        realtimeDeparture
        realtimeState
      }
    }
  }
}
""".strip()