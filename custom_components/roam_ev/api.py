"""ROAM EV Charging API client."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

import aiohttp

from .const import (
    API_BASE_URL,
    FIREBASE_API_KEY,
    FIREBASE_AUTH_URL,
    FIREBASE_REFRESH_URL,
    FIRESTORE_PROJECT_ID,
    FIRESTORE_URL,
    CHARGER_URL,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class SessionData:
    """Data class for charging session."""

    charger_id: str | None = None
    evse_id: str | None = None
    transaction_id: str | None = None
    status: int | None = None
    started_charging_at: str | None = None
    qr_code: str | None = None
    manual_input_code: str | None = None
    rate_applied: Any = None
    updated_at: str | None = None
    power: int = 0
    energy: int = 0
    energy_updated_at: str | None = None
    # Charger detail fields (populated by coordinator from cached charger data)
    charger_name: str | None = None
    charger_location: str | None = None
    connector_type: str | None = None
    max_power: float | None = None

    @property
    def is_active(self) -> bool:
        """Check if session is active."""
        return (
            (self.status is not None and self.status > 0)
            or self.charger_id is not None
            or self.evse_id is not None
            or self.transaction_id is not None
        )

    @property
    def numeric_rate(self) -> float | None:
        """Extract a numeric rate (per kWh) from rate_applied.

        rate_applied may be a number, a string, or a Firestore map
        containing a nested rate/price field.
        """
        if self.rate_applied is None:
            return None
        if isinstance(self.rate_applied, (int, float)):
            return float(self.rate_applied)
        if isinstance(self.rate_applied, str):
            try:
                return float(self.rate_applied)
            except ValueError:
                return None
        if isinstance(self.rate_applied, dict):
            # Firestore map — look for common field names
            for key in ("rate", "price", "pricePerKwh", "ratePerKwh", "amount"):
                val = self.rate_applied.get(key)
                if val is not None:
                    # Values may still be wrapped in Firestore type objects
                    if isinstance(val, dict):
                        for type_key in ("doubleValue", "integerValue", "stringValue"):
                            if type_key in val:
                                try:
                                    return float(val[type_key])
                                except (ValueError, TypeError):
                                    continue
                    elif isinstance(val, (int, float)):
                        return float(val)
        return None

    @property
    def session_cost(self) -> float | None:
        """Estimate the current session cost (energy_Wh / 1000 * rate_per_kWh)."""
        rate = self.numeric_rate
        if rate is None or not self.energy:
            return None
        return round(self.energy / 1000.0 * rate, 2)


@dataclass
class ChargerData:
    """Data class for charger information."""

    charger_id: str | None = None
    name: str | None = None
    location: str | None = None
    connector_type: str | None = None
    max_power: int | None = None
    raw_data: dict | None = None


class RoamEVApiError(Exception):
    """Exception for ROAM EV API errors."""


class RoamEVAuthError(RoamEVApiError):
    """Exception for authentication errors."""


class RoamEVApi:
    """ROAM EV API client."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        email: str | None = None,
        password: str | None = None,
    ) -> None:
        """Initialize the API client."""
        self._session = session
        self._email = email
        self._password = password
        self._id_token: str | None = None
        self._refresh_token: str | None = None
        self._user_id: str | None = None
        self._token_expiry: datetime | None = None

    @property
    def user_id(self) -> str | None:
        """Return the user ID."""
        return self._user_id

    @property
    def refresh_token(self) -> str | None:
        """Return the refresh token."""
        return self._refresh_token

    @property
    def id_token(self) -> str | None:
        """Return the ID token."""
        return self._id_token

    def set_tokens(
        self,
        id_token: str,
        refresh_token: str,
        user_id: str,
        expires_in: int = 0,
    ) -> None:
        """Set tokens from stored values.

        When restoring tokens from storage, expires_in should be 0 (default)
        to force a refresh on the next API call, since we don't know when
        the token was originally issued.
        """
        self._id_token = id_token
        self._refresh_token = refresh_token
        self._user_id = user_id
        if expires_in > 0:
            self._token_expiry = datetime.now() + timedelta(seconds=expires_in)
        else:
            # Force refresh on next use
            self._token_expiry = datetime.now()

    async def authenticate(self) -> dict[str, Any]:
        """Authenticate with Firebase using email/password."""
        if not self._email or not self._password:
            raise RoamEVAuthError("Email and password required for authentication")

        url = f"{FIREBASE_AUTH_URL}?key={FIREBASE_API_KEY}"
        payload = {
            "email": self._email,
            "password": self._password,
            "returnSecureToken": True,
        }

        try:
            async with self._session.post(url, json=payload) as response:
                data = await response.json()

                if response.status != 200:
                    error_message = data.get("error", {}).get("message", "Unknown error")
                    _LOGGER.error("Firebase auth failed: %s", error_message)
                    raise RoamEVAuthError(f"Authentication failed: {error_message}")

                self._id_token = data["idToken"]
                self._refresh_token = data["refreshToken"]
                self._user_id = data["localId"]
                expires_in = int(data.get("expiresIn", 3600))
                self._token_expiry = datetime.now() + timedelta(seconds=expires_in)

                _LOGGER.debug("Successfully authenticated user: %s", self._user_id)
                return data

        except aiohttp.ClientError as err:
            raise RoamEVApiError(f"Connection error during authentication: {err}") from err

    async def refresh_auth_token(self) -> dict[str, Any]:
        """Refresh the authentication token."""
        if not self._refresh_token:
            raise RoamEVAuthError("No refresh token available")

        url = f"{FIREBASE_REFRESH_URL}?key={FIREBASE_API_KEY}"
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": self._refresh_token,
        }

        try:
            async with self._session.post(url, json=payload) as response:
                data = await response.json()

                if response.status != 200:
                    error_message = data.get("error", {}).get("message", "Unknown error")
                    _LOGGER.error("Token refresh failed: %s", error_message)
                    raise RoamEVAuthError(f"Token refresh failed: {error_message}")

                self._id_token = data["id_token"]
                self._refresh_token = data["refresh_token"]
                self._user_id = data["user_id"]
                expires_in = int(data.get("expires_in", 3600))
                self._token_expiry = datetime.now() + timedelta(seconds=expires_in)

                _LOGGER.debug("Successfully refreshed token")
                return data

        except aiohttp.ClientError as err:
            raise RoamEVApiError(f"Connection error during token refresh: {err}") from err

    async def _ensure_valid_token(self) -> None:
        """Ensure we have a valid token, refreshing if necessary."""
        if not self._id_token:
            if self._email and self._password:
                await self.authenticate()
            else:
                raise RoamEVAuthError("Not authenticated")
            return

        # Refresh if token expires in less than 5 minutes
        if self._token_expiry and datetime.now() > self._token_expiry - timedelta(minutes=5):
            _LOGGER.debug("Token expiring soon, refreshing...")
            try:
                await self.refresh_auth_token()
            except RoamEVAuthError:
                # Refresh token may be invalid, fall back to full re-authentication
                if self._email and self._password:
                    _LOGGER.debug("Token refresh failed, attempting full re-authentication")
                    await self.authenticate()
                else:
                    raise

    def _parse_firestore_value(self, field: dict | None) -> Any:
        """Parse a Firestore field value."""
        if not field:
            return None
        if "stringValue" in field:
            return field["stringValue"]
        if "integerValue" in field:
            return int(field["integerValue"])
        if "doubleValue" in field:
            return field["doubleValue"]
        if "booleanValue" in field:
            return field["booleanValue"]
        if "timestampValue" in field:
            return field["timestampValue"]
        if "mapValue" in field:
            return field["mapValue"].get("fields", {})
        if "nullValue" in field:
            return None
        return None

    async def _reauthenticate(self) -> None:
        """Force re-authentication by refreshing token or doing full login."""
        self._token_expiry = None
        self._id_token = None
        try:
            if self._refresh_token:
                await self.refresh_auth_token()
                return
        except RoamEVAuthError:
            _LOGGER.debug("Refresh failed during reauthentication, trying full login")

        if self._email and self._password:
            await self.authenticate()
        else:
            raise RoamEVAuthError("Cannot re-authenticate: no credentials available")

    async def get_user_data(self) -> dict[str, Any]:
        """Get user document from Firestore."""
        return await self._get_user_data_with_retry()

    async def _get_user_data_with_retry(self, retried: bool = False) -> dict[str, Any]:
        """Get user document from Firestore, retrying once on auth failure."""
        await self._ensure_valid_token()

        url = FIRESTORE_URL.format(project=FIRESTORE_PROJECT_ID, user_id=self._user_id)
        headers = {
            "Authorization": f"Bearer {self._id_token}",
            "Content-Type": "application/json",
        }

        try:
            async with self._session.get(url, headers=headers) as response:
                if response.status in (401, 403) and not retried:
                    _LOGGER.debug("Auth rejected by Firestore (HTTP %s), re-authenticating", response.status)
                    await self._reauthenticate()
                    return await self._get_user_data_with_retry(retried=True)

                if response.status != 200:
                    text = await response.text()
                    if response.status in (401, 403):
                        raise RoamEVAuthError(f"Authentication failed: {response.status}")
                    _LOGGER.error("Failed to get user data: %s", text)
                    raise RoamEVApiError(f"Failed to get user data: {response.status}")

                data = await response.json()
                fields = data.get("fields", {})

                # Parse current session
                current_session_raw = self._parse_firestore_value(fields.get("currentSession"))
                session_data = None

                if current_session_raw and isinstance(current_session_raw, dict):
                    session_data = {
                        "charger_id": self._parse_firestore_value(current_session_raw.get("chargerId")),
                        "evse_id": self._parse_firestore_value(current_session_raw.get("evseId")),
                        "transaction_id": self._parse_firestore_value(current_session_raw.get("transactionId")),
                        "status": self._parse_firestore_value(current_session_raw.get("status")),
                        "started_charging_at": self._parse_firestore_value(current_session_raw.get("startedChargingAt")),
                        "qr_code": self._parse_firestore_value(current_session_raw.get("qrCode")),
                        "manual_input_code": self._parse_firestore_value(current_session_raw.get("manualInputCode")),
                        "rate_applied": self._parse_firestore_value(current_session_raw.get("rateApplied")),
                        "updated_at": self._parse_firestore_value(current_session_raw.get("updatedAt")),
                    }

                # Parse current session energy
                energy_raw = self._parse_firestore_value(fields.get("currentSessionEnergy"))
                energy_data = None

                if energy_raw and isinstance(energy_raw, dict):
                    energy_data = {
                        "power": self._parse_firestore_value(energy_raw.get("power")) or 0,
                        "energy": self._parse_firestore_value(energy_raw.get("energy")) or 0,
                        "updated_at": self._parse_firestore_value(energy_raw.get("updatedAt")),
                    }

                return {
                    "current_session": session_data,
                    "current_session_energy": energy_data,
                    "email": self._parse_firestore_value(fields.get("email")),
                    "first_login": self._parse_firestore_value(fields.get("firstLogin")),
                }

        except aiohttp.ClientError as err:
            raise RoamEVApiError(f"Connection error getting user data: {err}") from err

    async def get_charger_details(self, charger_id: str) -> dict[str, Any]:
        """Get charger details from API."""
        return await self._get_charger_details_with_retry(charger_id)

    async def _get_charger_details_with_retry(
        self, charger_id: str, retried: bool = False
    ) -> dict[str, Any]:
        """Get charger details from API, retrying once on auth failure."""
        await self._ensure_valid_token()

        url = CHARGER_URL.format(base=API_BASE_URL, charger_id=charger_id)
        headers = {
            "Authorization": f"Bearer {self._id_token}",
            "Content-Type": "application/json",
        }

        try:
            async with self._session.get(url, headers=headers) as response:
                if response.status in (401, 403) and not retried:
                    _LOGGER.debug("Auth rejected by charger API (HTTP %s), re-authenticating", response.status)
                    await self._reauthenticate()
                    return await self._get_charger_details_with_retry(charger_id, retried=True)

                if response.status != 200:
                    text = await response.text()
                    _LOGGER.warning("Failed to get charger details: %s", text)
                    return {}

                return await response.json()

        except aiohttp.ClientError as err:
            _LOGGER.warning("Connection error getting charger details: %s", err)
            return {}

    async def get_session_data(self) -> SessionData:
        """Get current session data."""
        user_data = await self.get_user_data()

        session = SessionData()
        session_info = user_data.get("current_session")
        energy_info = user_data.get("current_session_energy")

        if session_info:
            session.charger_id = session_info.get("charger_id")
            session.evse_id = session_info.get("evse_id")
            session.transaction_id = session_info.get("transaction_id")
            session.status = session_info.get("status")
            session.started_charging_at = session_info.get("started_charging_at")
            session.qr_code = session_info.get("qr_code")
            session.manual_input_code = session_info.get("manual_input_code")
            session.rate_applied = session_info.get("rate_applied")
            session.updated_at = session_info.get("updated_at")

        if energy_info:
            session.power = energy_info.get("power", 0)
            session.energy = energy_info.get("energy", 0)
            session.energy_updated_at = energy_info.get("updated_at")

        return session

