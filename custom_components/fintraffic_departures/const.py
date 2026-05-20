from __future__ import annotations

from datetime import timedelta

DOMAIN = "fintraffic_departures"

CONF_STOP_IDS = "stop_ids"
CONF_NUMBER_OF_DEPARTURES = "number_of_departures"
CONF_CUTOFF_MINUTES = "cutoff_minutes"

DEFAULT_NUMBER_OF_DEPARTURES = 4
DEFAULT_CUTOFF_MINUTES = 0
DEFAULT_UPDATE_INTERVAL = timedelta(seconds=60)

GRAPHQL_URL = "https://matkamonitori.digitransit.fi/api/graphql"
GRAPHQL_ENDPOINT_HEADER = "routing/v2/finland/gtfs/v1"

ATTR_PRIMARY_DEPARTURE = "primary_departure"
ATTR_NEXT_DEPARTURES = "next_departures"
ATTR_ALERTS = "alerts"
ATTR_STOP_ID = "stop_id"
ATTR_STOP_NAME = "stop_name"

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