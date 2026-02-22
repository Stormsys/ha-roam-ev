# CLAUDE.md — ha-roam-ev

## Project Overview

Home Assistant custom integration for **ROAM EV Charging**. Polls the ROAM EV cloud API (Firebase/Firestore-backed) to expose charging session data as HA sensors.

- **Domain:** `roam_ev`
- **IoT Class:** `cloud_polling` (30-second default interval, configurable 10–300s)
- **Version:** `0.1.0a1` (alpha, HACS-distributed)
- **Platforms:** `sensor`, `binary_sensor`

## Repository Structure

```
ha-roam-ev/
├── hacs.json                          # HACS integration metadata
├── custom_components/roam_ev/
│   ├── __init__.py                    # Entry setup, token restore, coordinator init
│   ├── api.py                         # RoamEVApi client (Firebase auth, Firestore queries)
│   ├── coordinator.py                 # DataUpdateCoordinator with token persistence
│   ├── config_flow.py                 # Config flow (setup + reauth + options)
│   ├── const.py                       # Constants (URLs, keys, defaults)
│   ├── sensor.py                      # 6 sensor entities (power, energy, charger, etc.)
│   ├── binary_sensor.py               # 1 binary sensor (charging session active)
│   ├── manifest.json                  # HA integration manifest
│   ├── strings.json                   # Base UI strings
│   ├── translations/en.json           # English translations
│   ├── icon.png                       # Integration icon
│   └── logo.png                       # Integration logo
├── evc_api_analysis.md                # API reverse-engineering notes (reference only)
└── final-version.js                   # Node.js prototype (reference only)
```

## Architecture & Key Concepts

### Authentication Flow (api.py)

Firebase email/password auth → ID token + refresh token. Tokens are:
1. Obtained during config flow setup
2. Stored in the config entry data
3. Restored on HA startup via `set_tokens()` (forces immediate refresh since stored tokens may be expired)
4. Auto-refreshed before expiry via `_ensure_valid_token()`
5. Falls back to full re-authentication if refresh fails
6. Retried once on 401/403 API responses via `_reauthenticate()`
7. Persisted back to config entry by the coordinator after any refresh

### Data Flow

```
Firebase Auth → Firestore user document → SessionData dataclass → Coordinator → Entities
```

- `RoamEVApi.get_session_data()` fetches the user document and parses `currentSession` + `currentSessionEnergy` fields
- `RoamEVCoordinator._async_update_data()` calls the API, caches charger details, persists new tokens
- Entities read from `coordinator.data` (a `SessionData` instance)

### Entity Design

All entities use `CoordinatorEntity` pattern with `_attr_has_entity_name = True` and `translation_key` for names. Device grouping uses email-based `DeviceInfo`.

**Sensors (sensor.py):** power (W), energy (Wh), charger_id, transaction_id, session_start (timestamp), session_status (text). Most are only `available` when a session is active.

**Binary sensor (binary_sensor.py):** `is_on` when `SessionData.is_active` is true. Exposes charging details as extra state attributes.

### Config Flow (config_flow.py)

- **User step:** Email + password → authenticate → store credentials + tokens
- **Reauth step:** Password only (email pre-filled) → re-authenticate → update entry
- **Options:** Scan interval (10–300 seconds, default 30)
- Unique ID: email (lowercased)

## External Services

| Service | URL Pattern | Purpose |
|---------|-------------|---------|
| Firebase Auth | `identitytoolkit.googleapis.com/v1/accounts:signInWithPassword` | Email/password login |
| Firebase Token | `securetoken.googleapis.com/v1/token` | Token refresh |
| Firestore | `firestore.googleapis.com/v1/projects/{project}/databases/(default)/documents/users/{user_id}` | User session data |
| ROAM API | `europe-west2-prod-evc-app.cloudfunctions.net/evc_charge/charger/{id}` | Charger details |

## Development Guidelines

### Code Style
- Python 3.11+ with `from __future__ import annotations`
- Type hints on all function signatures
- Dataclasses for data models (`SessionData`, `ChargerData`)
- `_LOGGER = logging.getLogger(__name__)` per module
- HA conventions: `async_setup_entry`, `async_unload_entry`, `CoordinatorEntity`, `ConfigFlow`

### Error Handling
- `RoamEVAuthError` (auth failures) → `ConfigEntryAuthFailed` → triggers HA reauth flow
- `RoamEVApiError` (connection/API failures) → `UpdateFailed` → coordinator retries next interval
- API calls retry once on 401/403 by re-authenticating before raising

### Adding New Sensors
1. Add a `RoamEVSensorEntityDescription` to the `SENSOR_DESCRIPTIONS` tuple in `sensor.py`
2. Set `value_fn` to extract from `SessionData`
3. Add translation key in `strings.json` and `translations/en.json` under `entity.sensor`

### Adding New Platforms
1. Add the platform to `PLATFORMS` in `__init__.py`
2. Create the platform module with `async_setup_entry`
3. Use `CoordinatorEntity[RoamEVCoordinator]` as the base

### HACS Distribution
- `hacs.json` at repo root configures HACS metadata
- Version in `manifest.json` follows PEP 440 (`0.1.0a1` = alpha)
- GitHub releases should tag versions matching `manifest.json`
- `codeowners` in manifest should match GitHub usernames

## Build & Test

No CI/test infrastructure currently exists. The integration is tested manually by installing in a Home Assistant instance.

**Manual testing:**
1. Copy `custom_components/roam_ev/` to your HA `custom_components/` directory
2. Restart Home Assistant
3. Add integration via Settings → Integrations → Add → "ROAM EV Charging"
4. Enter email/password for your ROAM EV account

## Common Pitfalls

- **Firestore field parsing:** All Firestore values are wrapped in type objects (`stringValue`, `integerValue`, etc.). Use `_parse_firestore_value()` to unwrap.
- **Token key names differ:** Firebase auth returns `idToken`/`refreshToken`/`localId`, but the refresh endpoint returns `id_token`/`refresh_token`/`user_id`.
- **Session "active" detection:** A session is considered active if any of status > 0, charger_id, evse_id, or transaction_id are set.
- **`aiohttp` is provided by HA:** Don't add it as a pip dependency beyond the `requirements` field in manifest.json. Use `async_get_clientsession()` to get the shared session.
