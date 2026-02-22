# ROAM EV Charging for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

A custom Home Assistant integration for monitoring your [ROAM EV](https://www.evc.co.uk/) charging sessions.

## Features

- **Charging Session Detection** — binary sensor that turns on when a session is active
- **Live Power Monitoring** — current charging power in watts
- **Energy Tracking** — total energy delivered per session in watt-hours
- **Session Cost & Tariff** — estimated cost, tariff rate, and last session cost
- **Session Status** — OCPP status (available, preparing, charging, suspended, finishing, etc.)
- **Charger Details** — charger name, location, connector type, and max power
- **Charger & Transaction IDs** — charger ID, EVSE ID, QR code, and manual input code
- **Session Timing** — start time, duration, and last-updated timestamps
- **Configurable Polling** — update interval from 10 to 300 seconds (default 30s)

## Installation

### HACS (Recommended)

1. Open HACS in your Home Assistant instance
2. Click the three dots menu → **Custom repositories**
3. Add `https://github.com/Stormsys/ha-roam-ev` with category **Integration**
4. Search for "ROAM EV Charging" and install
5. Restart Home Assistant

### Manual

1. Copy the `custom_components/roam_ev/` folder to your Home Assistant `custom_components/` directory
2. Restart Home Assistant

## Setup

1. Go to **Settings → Devices & Services → Add Integration**
2. Search for **ROAM EV Charging**
3. Enter your ROAM EV account email and password
4. The integration will authenticate and begin polling for session data

## Entities

| Entity | Type | Description |
|--------|------|-------------|
| Charging Session | Binary Sensor | On when a charging session is active |
| Charging Power | Sensor | Current power draw (W) |
| Energy Delivered | Sensor | Total energy this session (Wh) |
| Session Status | Sensor | OCPP status string (always available) |
| Session Cost | Sensor | Estimated cost of current session (GBP) |
| Last Session Cost | Sensor | Cost of the most recent completed session (GBP) |
| Tariff Rate | Sensor | Applied rate per kWh (GBP/kWh) |
| Session Duration | Sensor | Elapsed time since session started |
| Charger ID | Sensor | Active charger identifier |
| EVSE ID | Sensor | EVSE identifier (diagnostic) |
| Transaction ID | Sensor | Transaction identifier (diagnostic) |
| Charger Name | Sensor | Name of the active charger |
| Charger Location | Sensor | Location/address of the charger |
| Connector Type | Sensor | Connector type (e.g. Type 2) |
| Charger Max Power | Sensor | Maximum power rating of the charger (kW) |
| Session Start Time | Sensor | Timestamp when session started |
| Session Last Updated | Sensor | Timestamp of last session update (diagnostic) |
| Energy Last Updated | Sensor | Timestamp of last energy reading (diagnostic) |
| QR Code | Sensor | Charger QR code value (diagnostic) |
| Manual Input Code | Sensor | Charger manual input code (diagnostic) |

Most sensors are only available while a charging session is active. Session Status is always available.

## Options

After setup, you can configure:

- **Update interval** — how often to poll the ROAM API (10–300 seconds, default 30)

Go to **Settings → Devices & Services → ROAM EV Charging → Configure** to change options.

## Troubleshooting

### Integration shows "Authentication failed"

Your ROAM EV credentials may have changed, or the token could not be refreshed. Go to the integration page and follow the reauthentication flow to enter your updated password.

### Sensors show "Unavailable"

Most sensors only have values during an active charging session. When idle, only the Session Status sensor (showing "available") and the Charging Session binary sensor (showing "off") will be available.

## License

This project is provided as-is for personal use with the ROAM EV charging network.
