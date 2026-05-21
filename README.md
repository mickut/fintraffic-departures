# Transit Departures Finland

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)

[![hacs][hacsbadge]][hacs]
![Project Maintenance][maintenance-shield]

[![Community Forum][forum-shield]][forum]

Home Assistant custom integration for upcoming departures from the FinTraffic GraphQL API.

## Features

- Uses [FinTraffic open APIs](https://www.digitraffic.fi/en/) for public transit per-stop departure times
- Shared config entry for departure settings, plus one stop subentry per configured stop
- One stop-specific sensor per configured stop
- Stop setup by REST-based name lookup or manual GTFS id entry
- Configurable API polling interval with a default of 15 minutes
- Sensor values and attributes recalculated every minute from the latest retrieved data
- Timestamp sensor state for the next valid departure after the cutoff window
- Attributes for the primary departure, following departures, and active alerts

## Installation

### HACS

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=mickut&repository=ha-transit-departures)

1. Open HACS in Home Assistant.
2. Go to Integrations.
3. Open the three-dot menu and choose Custom repositories.
4. Add `https://github.com/mickut/ha-transit-departures` as a repository with category `Integration`.
5. Find Transit Departures Finland in HACS and install it.
6. Restart Home Assistant.
7. Go to Settings > Devices & services > Add integration and search for Transit Departures Finland.

### Manual installation

1. Download this repository.
2. Copy the `custom_components/transit_departures` folder into your Home Assistant `config/custom_components` directory.
3. Restart Home Assistant.
4. Go to Settings > Devices & services > Add integration and search for Transit Departures Finland.

## Configuration

The main config flow asks for:

- `number_of_departures`: how many departures to retain after sorting and filtering
- `cutoff_minutes`: exclude departures that are in the past or within this many minutes from now
- `update_interval_minutes`: API polling interval for refreshing departures, default `15`

After the main entry is created, Home Assistant opens a stop subentry flow for the first stop. Additional stops can be added later from the integration page.

Each stop can be added in one of two ways:

- Search by stop name using the DigiTransit geocoding endpoint and select one matching stop
- Enter the stop GTFS id manually, for example `MATKA:12345`

## Sensor behavior

Each sensor uses the next departure datetime as its state. Route names and related metadata are exposed in attributes because a Home Assistant sensor state can only hold one value. The integration recalculates sensor state and attributes once a minute from cached API data, while the external API call itself follows the configured interval.

Main attributes:

- `primary_departure`
- `next_departures`
- `alerts`
- `stop_id`
- `stop_name`

***

[commits-shield]: https://img.shields.io/github/commit-activity/y/mickut/ha-transit-departures.svg?style=for-the-badge
[commits]: https://github.com/mickut/ha-transit-departures/commits/main
[hacs]: https://github.com/custom-components/hacs
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
[forum-shield]: https://img.shields.io/badge/community-forum-brightgreen.svg?style=for-the-badge
[forum]: https://community.home-assistant.io/
[license-shield]: https://img.shields.io/github/license/mickut/ha-transit-departures.svg?style=for-the-badge
[maintenance-shield]: https://img.shields.io/badge/maintainer-Antti%20Kuntsi%20%40mickut-blue.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/mickut/ha-transit-departures.svg?style=for-the-badge
[releases]: https://github.com/mickut/ha-transit-departures/releases
