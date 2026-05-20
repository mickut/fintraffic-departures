from __future__ import annotations

import json
from datetime import timedelta
from pathlib import Path

DOMAIN = "fintraffic_departures"

CONF_STOP_ID = "stop_id"
CONF_STOP_LOOKUP_QUERY = "stop_lookup_query"
CONF_NUMBER_OF_DEPARTURES = "number_of_departures"
CONF_CUTOFF_MINUTES = "cutoff_minutes"
CONF_UPDATE_INTERVAL_MINUTES = "update_interval_minutes"
SUBENTRY_TYPE_STOP = "stop"

DEFAULT_NUMBER_OF_DEPARTURES = 4
DEFAULT_CUTOFF_MINUTES = 0
DEFAULT_UPDATE_INTERVAL_MINUTES = 15
COORDINATOR_UPDATE_INTERVAL = timedelta(minutes=1)

GRAPHQL_URL = "https://matkamonitori.digitransit.fi/api/graphql"
GEOCODING_SEARCH_URL = "https://matkamonitori.digitransit.fi/api/geocoding/search"
GRAPHQL_ENDPOINT_VALUE = "routing/v2/finland/gtfs/v1"
GRAPHQL_USER_HEADER = "Digitraffic-User"
GEOCODING_SEARCH_SIZE = 40
GEOCODING_SEARCH_LAYERS = "stop,station"
GEOCODING_SEARCH_SOURCES = (
  "gtfsMATKA,gtfsCAR_FERRIES,gtfsHSL,gtfstampere,gtfsLINKKI,gtfsOULU,"
  "gtfsdigitraffic,gtfsRauma,gtfsHameenlinna,gtfsKotka,gtfsKouvola,"
  "gtfsLappeenranta,gtfsMikkeli,gtfsVaasa,gtfsJoensuu,gtfsFOLI,gtfsLahti,"
  "gtfsKuopio,gtfsRovaniemi,gtfsKajaani,gtfsSalo,gtfsPori,gtfsRaasepori,"
  "gtfsVikingline,gtfsVARELY,gtfsHarma,gtfsPohjolanMatka,gtfsKorsisaari,"
  "gtfsKoivistonAuto,gtfsPahkakankaanLiikenne,gtfsIngvesSvanback"
)

ATTR_PRIMARY_DEPARTURE = "primary_departure"
ATTR_NEXT_DEPARTURES = "next_departures"
ATTR_ALERTS = "alerts"
ATTR_STOP_ID = "stop_id"
ATTR_STOP_NAME = "stop_name"


def normalize_stop_id(stop_id: str) -> str:
  normalized = stop_id.strip()
  if normalized.startswith("GTFS:"):
    return normalized[5:]
  return normalized


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