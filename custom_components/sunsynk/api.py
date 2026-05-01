"""Sunsynk Cloud API client and payload normalization."""

from __future__ import annotations

import asyncio
import base64
from dataclasses import dataclass
from datetime import date, datetime
import hashlib
import logging
import re
import time
from typing import Any, Mapping
from urllib.parse import urlparse

_LOGGER = logging.getLogger(__name__)

REQUEST_TIMEOUT_SECONDS = 20
QUERY_REQUEST_MIN_INTERVAL_SECONDS = 1.0
CLIENT_ID = "csp-web"

_CAMEL_CASE_PATTERN = re.compile(r"(?<!^)(?=[A-Z])")


class SunsynkApiError(Exception):
    """Base Sunsynk API exception."""


class SunsynkAuthenticationError(SunsynkApiError):
    """Raised when Sunsynk rejects credentials or the access token."""


class SunsynkCannotConnectError(SunsynkApiError):
    """Raised when Home Assistant cannot reach Sunsynk Cloud."""


class SunsynkUnsupportedSettingError(SunsynkApiError):
    """Raised when a settings payload cannot safely support a write."""


class SunsynkSettingsWriteError(SunsynkApiError):
    """Raised when a Sunsynk settings write is not confirmed by readback."""


@dataclass(slots=True)
class SunsynkInverter:
    """Sunsynk inverter summary."""

    serial: str
    name: str | None
    plant_id: str | None
    plant_name: str | None
    model: str | None
    gateway_serial: str | None
    raw: dict[str, Any]


@dataclass(frozen=True, slots=True)
class SunsynkSample:
    """A normalized value from a Sunsynk payload."""

    value: Any
    unit: str | None
    source: str
    name: str
    raw_key: str
    updated_at: str | None = None


@dataclass(slots=True)
class SunsynkApiUsageStats:
    """Per-device daily API usage counters."""

    day: date
    calls: int = 0
    errors: int = 0
    last_called_at: datetime | None = None
    last_error_at: datetime | None = None


SYSTEM_MODE_SETTING_FIELDS: tuple[str, ...] = (
    "sn",
    "safetyType",
    "battMode",
    "solarSell",
    "pvMaxLimit",
    "energyMode",
    "peakAndVallery",
    "sysWorkMode",
    "sellTime1",
    "sellTime2",
    "sellTime3",
    "sellTime4",
    "sellTime5",
    "sellTime6",
    "sellTime1Pac",
    "sellTime2Pac",
    "sellTime3Pac",
    "sellTime4Pac",
    "sellTime5Pac",
    "sellTime6Pac",
    "cap1",
    "cap2",
    "cap3",
    "cap4",
    "cap5",
    "cap6",
    "sellTime1Volt",
    "sellTime2Volt",
    "sellTime3Volt",
    "sellTime4Volt",
    "sellTime5Volt",
    "sellTime6Volt",
    "zeroExportPower",
    "solarMaxSellPower",
    "mondayOn",
    "tuesdayOn",
    "wednesdayOn",
    "thursdayOn",
    "fridayOn",
    "saturdayOn",
    "sundayOn",
    "time1on",
    "time2on",
    "time3on",
    "time4on",
    "time5on",
    "time6on",
    "genTime1on",
    "genTime2on",
    "genTime3on",
    "genTime4on",
    "genTime5on",
    "genTime6on",
)

SUPPORTED_SETTING_VALUES: Mapping[str, frozenset[int]] = {
    "sysWorkMode": frozenset({0, 1, 2}),
    "energyMode": frozenset({0, 1}),
    "peakAndVallery": frozenset({0, 1}),
}


class SunsynkApiClient:
    """Small async wrapper around Sunsynk Cloud endpoints."""

    def __init__(
        self,
        session: Any,
        username: str,
        password: str,
        *,
        base_url: str,
    ) -> None:
        """Initialize the API client."""
        self._session = session
        self._username = username
        self._password = password
        self._base_url = _normalize_base_url(base_url)
        self._source = _source_for_base_url(self._base_url)
        self._access_token: str | None = None
        self._refresh_token: str | None = None
        self._login_lock = asyncio.Lock()
        self._path_locks: dict[str, asyncio.Lock] = {}
        self._last_request_started: dict[str, float] = {}
        self._usage_by_device: dict[str, SunsynkApiUsageStats] = {}

    async def async_login(self) -> None:
        """Authenticate and store an access token."""
        async with self._login_lock:
            await self._async_login()

    async def _async_refresh_login(self, expired_token: str | None) -> None:
        """Refresh auth unless another request already replaced the token."""
        async with self._login_lock:
            if self._access_token and self._access_token != expired_token:
                return
            await self._async_login()

    async def _async_login(self) -> None:
        """Authenticate without taking the login lock."""
        public_key = await self._async_fetch_public_key()
        encrypted_password = _rsa_encrypt_pkcs1v15(public_key, self._password)

        nonce = _make_nonce()
        sign = _md5_hex(f"nonce={nonce}&source={self._source}{public_key[:10]}")
        payload = {
            "client_id": CLIENT_ID,
            "grant_type": "password",
            "password": encrypted_password,
            "source": self._source,
            "username": self._username,
            "nonce": nonce,
            "sign": sign,
        }

        try:
            data = await self._async_request(
                "POST",
                "/oauth/token/new",
                payload=payload,
                authenticated=False,
            )
        except SunsynkCannotConnectError:
            raise
        except SunsynkApiError as err:
            raise SunsynkAuthenticationError(str(err)) from err
        token_data = data.get("data")
        if not isinstance(token_data, dict) or not token_data.get("access_token"):
            raise SunsynkAuthenticationError("Sunsynk login did not return an access token")

        self._access_token = str(token_data["access_token"])
        self._refresh_token = (
            str(token_data["refresh_token"]) if token_data.get("refresh_token") else None
        )

    async def async_list_inverters(self) -> list[SunsynkInverter]:
        """Return inverters visible to the Sunsynk account."""
        data = await self._async_request(
            "GET",
            "/api/v1/inverters",
            params={
                "page": 1,
                "limit": 100,
                "total": 0,
                "status": -1,
                "sn": "",
                "plantId": "",
                "type": -2,
                "softVer": "",
                "hmiVer": "",
                "agentCompanyId": -1,
                "gsn": "",
            },
        )
        rows = _extract_infos(data)
        inverters: list[SunsynkInverter] = []

        for item in rows:
            serial = item.get("sn") or item.get("serial") or item.get("inverterSn")
            if not serial:
                continue
            plant = item.get("plant") if isinstance(item.get("plant"), dict) else {}
            gateway = (
                item.get("gatewayVO") if isinstance(item.get("gatewayVO"), dict) else {}
            )
            inverters.append(
                SunsynkInverter(
                    serial=str(serial),
                    name=_empty_to_none(item.get("alias") or item.get("name")),
                    plant_id=_string_or_none(plant.get("id") or item.get("plantId")),
                    plant_name=_empty_to_none(plant.get("name") or item.get("plantName")),
                    model=_empty_to_none(item.get("model") or item.get("equipMode")),
                    gateway_serial=_empty_to_none(item.get("gsn") or gateway.get("gsn")),
                    raw=item,
                )
            )

        return inverters

    async def async_get_inverter_info(self, serial: str) -> dict[str, Any]:
        """Return high-level inverter metadata."""
        return await self._async_get_data(f"/api/v1/inverter/{serial}", serial)

    async def async_get_realtime_input(self, serial: str) -> dict[str, Any]:
        """Return realtime PV input data."""
        return await self._async_get_data(
            f"/api/v1/inverter/{serial}/realtime/input", serial
        )

    async def async_get_realtime_output(self, serial: str) -> dict[str, Any]:
        """Return realtime inverter output data."""
        return await self._async_get_data(
            f"/api/v1/inverter/{serial}/realtime/output", serial
        )

    async def async_get_realtime_grid(self, serial: str) -> dict[str, Any]:
        """Return realtime grid data."""
        return await self._async_get_data(
            f"/api/v1/inverter/grid/{serial}/realtime",
            serial,
            params={"sn": serial},
        )

    async def async_get_realtime_battery(self, serial: str) -> dict[str, Any]:
        """Return realtime battery data."""
        return await self._async_get_data(
            f"/api/v1/inverter/battery/{serial}/realtime",
            serial,
            params={"sn": serial, "lan": "en"},
        )

    async def async_get_realtime_load(self, serial: str) -> dict[str, Any]:
        """Return realtime load data."""
        return await self._async_get_data(
            f"/api/v1/inverter/load/{serial}/realtime",
            serial,
            params={"sn": serial},
        )

    async def async_get_settings(self, serial: str) -> dict[str, Any]:
        """Return inverter settings readback data, if the account can access it."""
        return await self._async_get_data(f"/api/v1/common/setting/{serial}/read", serial)

    async def async_set_settings(
        self,
        serial: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """Write inverter settings using the Sunsynk system-mode payload."""
        return await self._async_request(
            "POST",
            f"/api/v1/common/setting/{serial}/set",
            payload=payload,
            device_serial=serial,
        )

    def get_daily_usage(self, serial: str) -> SunsynkApiUsageStats:
        """Return today's per-inverter API usage bucket."""
        return self._get_usage_bucket(serial)

    async def _async_get_data(
        self,
        path: str,
        serial: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Return the `data` object from a Sunsynk API response."""
        data = await self._async_request("GET", path, params=params, device_serial=serial)
        payload = data.get("data")
        return payload if isinstance(payload, dict) else {}

    async def _async_fetch_public_key(self) -> str:
        """Return the public key used to encrypt the password."""
        nonce = _make_nonce()
        sign = _md5_hex(f"nonce={nonce}&source={self._source}POWER_VIEW")
        data = await self._async_request(
            "GET",
            "/anonymous/publicKey",
            params={"source": self._source, "nonce": nonce, "sign": sign},
            authenticated=False,
        )
        public_key = data.get("data")
        if not public_key:
            raise SunsynkAuthenticationError("Sunsynk did not return a public key")
        return str(public_key)

    async def _async_request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        payload: dict[str, Any] | None = None,
        authenticated: bool = True,
        device_serial: str | None = None,
        retry_auth: bool = True,
    ) -> dict[str, Any]:
        """Send a request and validate the standard Sunsynk response shape."""
        if authenticated and self._access_token is None:
            await self.async_login()

        normalized_path = _normalize_path(path)
        url = f"{self._base_url}{normalized_path}"
        await self._async_wait_for_rate_limit(normalized_path)
        if device_serial:
            self._record_request(device_serial)

        request_token = self._access_token
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if authenticated and request_token:
            headers["Authorization"] = f"Bearer {request_token}"

        try:
            async with asyncio.timeout(REQUEST_TIMEOUT_SECONDS):
                response = await self._session.request(
                    method,
                    url,
                    headers=headers,
                    json=payload,
                    params=params,
                )
        except TimeoutError as err:
            self._record_request_error(device_serial)
            raise SunsynkCannotConnectError("Timed out contacting Sunsynk Cloud") from err
        except Exception as err:
            self._record_request_error(device_serial)
            raise SunsynkCannotConnectError("Unable to connect to Sunsynk Cloud") from err

        try:
            data = await response.json(content_type=None)
        except Exception as err:
            self._record_request_error(device_serial)
            text = await response.text()
            raise SunsynkApiError(f"Invalid Sunsynk response: {text}") from err

        if response.status == 401 and authenticated and retry_auth:
            await self._async_refresh_login(request_token)
            return await self._async_request(
                method,
                path,
                params=params,
                payload=payload,
                authenticated=authenticated,
                device_serial=device_serial,
                retry_auth=False,
            )

        if response.status >= 400:
            self._record_request_error(device_serial)
            raise SunsynkApiError(
                f"Sunsynk returned HTTP {response.status}: {data.get('msg', 'Unknown error')}"
            )

        if not _response_success(data):
            self._record_request_error(device_serial)
            message = data.get("msg") or data.get("message") or "Sunsynk request failed"
            if "token" in str(message).lower() or "auth" in str(message).lower():
                raise SunsynkAuthenticationError(str(message))
            raise SunsynkApiError(str(message))

        return data

    async def _async_wait_for_rate_limit(self, path: str) -> None:
        """Space out calls to the same endpoint path."""
        lock = self._path_locks.setdefault(path, asyncio.Lock())
        async with lock:
            now = time.monotonic()
            last_started = self._last_request_started.get(path)
            if last_started is not None:
                wait_time = QUERY_REQUEST_MIN_INTERVAL_SECONDS - (now - last_started)
                if wait_time > 0:
                    await asyncio.sleep(wait_time)
            self._last_request_started[path] = time.monotonic()

    def _record_request(self, serial: str | None) -> None:
        """Record an outbound request for diagnostics."""
        if serial is None:
            return
        usage = self._get_usage_bucket(serial)
        usage.calls += 1
        usage.last_called_at = datetime.now().astimezone()

    def _record_request_error(self, serial: str | None) -> None:
        """Record a failed outbound request for diagnostics."""
        if serial is None:
            return
        usage = self._get_usage_bucket(serial)
        usage.errors += 1
        usage.last_error_at = datetime.now().astimezone()

    def _get_usage_bucket(self, serial: str) -> SunsynkApiUsageStats:
        """Return the local-day usage bucket for a device."""
        today = datetime.now().astimezone().date()
        usage = self._usage_by_device.get(serial)
        if usage is None or usage.day != today:
            usage = SunsynkApiUsageStats(day=today)
            self._usage_by_device[serial] = usage
        return usage


def normalize_monitoring_payloads(
    *,
    input_data: dict[str, Any] | None = None,
    output_data: dict[str, Any] | None = None,
    grid_data: dict[str, Any] | None = None,
    battery_data: dict[str, Any] | None = None,
    load_data: dict[str, Any] | None = None,
    info_data: dict[str, Any] | None = None,
) -> dict[str, SunsynkSample]:
    """Flatten Sunsynk payloads into stable HA-facing sample keys."""
    values: dict[str, SunsynkSample] = {}
    input_data = input_data or {}
    output_data = output_data or {}
    grid_data = grid_data or {}
    battery_data = battery_data or {}
    load_data = load_data or {}
    info_data = info_data or {}

    _add(values, "solar_power", _sum_pv_power(input_data), "W", "input", "Solar Power", "pvIV.ppv")
    _add(values, "solar_energy_today", input_data.get("etoday"), "kWh", "input", "Solar Energy Today", "etoday")
    _add(values, "solar_energy_total", input_data.get("etotal"), "kWh", "input", "Solar Energy Total", "etotal")
    for item in _list_of_dicts(input_data.get("pvIV")):
        pv_no = item.get("pvNo")
        if pv_no is None:
            continue
        prefix = f"pv_{pv_no}"
        updated_at = _string_or_none(item.get("time"))
        _add(values, f"{prefix}_voltage", item.get("vpv"), "V", "input", f"PV {pv_no} Voltage", "vpv", updated_at)
        _add(values, f"{prefix}_current", item.get("ipv"), "A", "input", f"PV {pv_no} Current", "ipv", updated_at)
        _add(values, f"{prefix}_power", item.get("ppv"), "W", "input", f"PV {pv_no} Power", "ppv", updated_at)
        _add(values, f"{prefix}_energy_today", item.get("todayPv"), "kWh", "input", f"PV {pv_no} Energy Today", "todayPv", updated_at)

    _add(values, "inverter_power", output_data.get("pac"), "W", "output", "Inverter Power", "pac")
    _add(values, "inverter_internal_power", output_data.get("pInv"), "W", "output", "Inverter Internal Power", "pInv")
    _add(values, "inverter_frequency", output_data.get("fac"), "Hz", "output", "Inverter Frequency", "fac")
    _add_vip(values, "inverter_phase", output_data.get("vip"), "output")

    _add(values, "grid_power", grid_data.get("pac"), "W", "grid", "Grid Power", "pac")
    _add(values, "grid_frequency", grid_data.get("fac"), "Hz", "grid", "Grid Frequency", "fac")
    _add(values, "grid_power_factor", grid_data.get("pf"), None, "grid", "Grid Power Factor", "pf")
    _add(values, "grid_import_today", grid_data.get("etodayFrom"), "kWh", "grid", "Grid Import Today", "etodayFrom")
    _add(values, "grid_export_today", grid_data.get("etodayTo"), "kWh", "grid", "Grid Export Today", "etodayTo")
    _add(values, "grid_import_total", grid_data.get("etotalFrom"), "kWh", "grid", "Grid Import Total", "etotalFrom")
    _add(values, "grid_export_total", grid_data.get("etotalTo"), "kWh", "grid", "Grid Export Total", "etotalTo")
    _add_vip(values, "grid_phase", grid_data.get("vip"), "grid")

    _add(values, "battery_soc", battery_data.get("soc"), "%", "battery", "Battery SOC", "soc")
    _add(values, "battery_power", battery_data.get("power"), "W", "battery", "Battery Power", "power")
    _add(values, "battery_voltage", battery_data.get("voltage"), "V", "battery", "Battery Voltage", "voltage")
    _add(values, "battery_current", battery_data.get("current"), "A", "battery", "Battery Current", "current")
    _add(values, "battery_temperature", battery_data.get("temp"), "C", "battery", "Battery Temperature", "temp")
    _add(values, "battery_charge_today", battery_data.get("etodayChg"), "kWh", "battery", "Battery Charge Today", "etodayChg")
    _add(values, "battery_discharge_today", battery_data.get("etodayDischg"), "kWh", "battery", "Battery Discharge Today", "etodayDischg")
    _add(values, "battery_charge_total", battery_data.get("etotalChg"), "kWh", "battery", "Battery Charge Total", "etotalChg")
    _add(values, "battery_discharge_total", battery_data.get("etotalDischg"), "kWh", "battery", "Battery Discharge Total", "etotalDischg")
    _add(values, "battery_charge_current_limit", battery_data.get("chargeCurrentLimit"), "A", "battery", "Battery Charge Current Limit", "chargeCurrentLimit")
    _add(values, "battery_discharge_current_limit", battery_data.get("dischargeCurrentLimit"), "A", "battery", "Battery Discharge Current Limit", "dischargeCurrentLimit")

    _add(values, "load_power", load_data.get("totalPower"), "W", "load", "Load Power", "totalPower")
    _add(values, "load_energy_today", load_data.get("dailyUsed"), "kWh", "load", "Load Energy Today", "dailyUsed")
    _add(values, "load_energy_total", load_data.get("totalUsed"), "kWh", "load", "Load Energy Total", "totalUsed")
    _add(values, "load_frequency", load_data.get("loadFac"), "Hz", "load", "Load Frequency", "loadFac")
    _add(values, "load_ups_power_total", load_data.get("upsPowerTotal"), "W", "load", "UPS Load Power", "upsPowerTotal")
    _add_vip(values, "load_phase", load_data.get("vip"), "load")

    _add(values, "inverter_status", info_data.get("status"), None, "info", "Inverter Status", "status")
    _add(values, "inverter_run_status", info_data.get("runStatus"), None, "info", "Inverter Run Status", "runStatus")
    _add(values, "inverter_rated_power", info_data.get("ratePower"), "W", "info", "Inverter Rated Power", "ratePower")
    _add(values, "inverter_energy_month", info_data.get("emonth"), "kWh", "info", "Inverter Energy This Month", "emonth")
    _add(values, "inverter_energy_year", info_data.get("eyear"), "kWh", "info", "Inverter Energy This Year", "eyear")

    return values


def normalize_key(key: str) -> str:
    """Normalize API keys to a stable snake_case key."""
    return _CAMEL_CASE_PATTERN.sub("_", key).replace("-", "_").replace("__", "_").lower()


def settings_command_supported(settings: Mapping[str, Any], serial: str) -> bool:
    """Return whether readback has enough data to build a safe write payload."""
    try:
        _validate_settings_command_base(settings, serial)
    except SunsynkUnsupportedSettingError:
        return False
    return True


def setting_update_supported(
    settings: Mapping[str, Any],
    serial: str,
    setting_key: str,
) -> bool:
    """Return whether a specific write key can be exposed for this inverter."""
    return (
        setting_key in SUPPORTED_SETTING_VALUES
        and setting_key in settings
        and settings_command_supported(settings, serial)
    )


def build_settings_command_payload(
    settings: Mapping[str, Any],
    serial: str,
    updates: Mapping[str, Any],
) -> dict[str, Any]:
    """Build the expected Sunsynk settings write body from readback plus updates."""
    _validate_settings_command_base(settings, serial)
    payload = {field: settings[field] for field in SYSTEM_MODE_SETTING_FIELDS}

    for key, value in updates.items():
        payload[key] = normalize_setting_update_value(key, value)

    return payload


def normalize_setting_update_value(setting_key: str, value: Any) -> int:
    """Validate and normalize a supported writable setting value."""
    allowed_values = SUPPORTED_SETTING_VALUES.get(setting_key)
    if allowed_values is None:
        raise SunsynkUnsupportedSettingError(
            f"Sunsynk setting {setting_key} is not supported for writing"
        )

    normalized = _coerce_setting_int(value)
    if normalized not in allowed_values:
        allowed = ", ".join(str(item) for item in sorted(allowed_values))
        raise SunsynkUnsupportedSettingError(
            f"Sunsynk setting {setting_key} must be one of: {allowed}"
        )
    return normalized


def setting_value_matches(
    settings: Mapping[str, Any],
    setting_key: str,
    expected_value: Any,
) -> bool:
    """Return whether settings readback confirms the expected setting value."""
    try:
        current = normalize_setting_update_value(setting_key, settings.get(setting_key))
        expected = normalize_setting_update_value(setting_key, expected_value)
    except SunsynkUnsupportedSettingError:
        return False
    return current == expected


def prettify_key(key: str) -> str:
    """Return a human-readable label for an API key."""
    return _CAMEL_CASE_PATTERN.sub(" ", key).replace("_", " ").replace("-", " ").title()


def _add(
    values: dict[str, SunsynkSample],
    key: str,
    value: Any,
    unit: str | None,
    source: str,
    name: str,
    raw_key: str,
    updated_at: str | None = None,
) -> None:
    """Add a sample when Sunsynk supplied a usable value."""
    value = coerce_value(value)
    if value is None:
        return
    values[key] = SunsynkSample(
        value=value,
        unit=unit,
        source=source,
        name=name,
        raw_key=raw_key,
        updated_at=updated_at,
    )


def _add_vip(
    values: dict[str, SunsynkSample],
    prefix: str,
    items: Any,
    source: str,
) -> None:
    """Add per-phase voltage/current/power values from a Sunsynk `vip` list."""
    for index, item in enumerate(_list_of_dicts(items), start=1):
        label = prefix.replace("_", " ").title()
        _add(values, f"{prefix}_{index}_voltage", item.get("volt"), "V", source, f"{label} {index} Voltage", "vip.volt")
        _add(values, f"{prefix}_{index}_current", item.get("current"), "A", source, f"{label} {index} Current", "vip.current")
        _add(values, f"{prefix}_{index}_power", item.get("power"), "W", source, f"{label} {index} Power", "vip.power")


def _sum_pv_power(data: dict[str, Any]) -> Any:
    """Return summed PV string power, falling back to input `pac`."""
    total = 0.0
    found = False
    for item in _list_of_dicts(data.get("pvIV")):
        value = coerce_value(item.get("ppv"))
        if isinstance(value, (int, float)):
            total += float(value)
            found = True
    return total if found else data.get("pac")


def _extract_infos(response: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract a list of row dictionaries from common Sunsynk response shapes."""
    data = response.get("data")
    if isinstance(data, dict):
        infos = data.get("infos")
        if isinstance(infos, list):
            return [item for item in infos if isinstance(item, dict)]
        rows = data.get("rows") or data.get("list")
        if isinstance(rows, list):
            return [item for item in rows if isinstance(item, dict)]
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    return []


def _list_of_dicts(value: Any) -> list[dict[str, Any]]:
    """Return dictionary items from a list-like payload value."""
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _response_success(data: dict[str, Any]) -> bool:
    """Return whether a Sunsynk response indicates success."""
    if data.get("success") is True:
        return True
    if data.get("msg") == "Success":
        return True
    return data.get("code") in (0, "0") and data.get("data") is not None


def _normalize_path(path: str) -> str:
    """Ensure API paths start with one slash."""
    return path if path.startswith("/") else f"/{path}"


def _normalize_base_url(base_url: str) -> str:
    """Return a usable absolute API base URL."""
    trimmed = base_url.strip().rstrip("/")
    if not trimmed.startswith(("https://", "http://")):
        trimmed = f"https://{trimmed}"
    return trimmed


def _source_for_base_url(base_url: str) -> str:
    """Infer the login source from the selected API host."""
    host = urlparse(base_url).netloc or base_url
    return "elinter" if host.lower().startswith("pv.inteless.com") else "sunsynk"


def _make_nonce() -> int:
    """Return a Sunsynk nonce in milliseconds."""
    return int(time.time() * 1000)


def _md5_hex(value: str) -> str:
    """Return the lowercase MD5 hex digest used by Sunsynk login."""
    return hashlib.md5(value.encode("utf-8")).hexdigest()


def _rsa_encrypt_pkcs1v15(raw_key: str, plaintext: str) -> str:
    """Encrypt a password with Sunsynk's public key."""
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import padding

    pem = f"-----BEGIN PUBLIC KEY-----\n{raw_key}\n-----END PUBLIC KEY-----".encode()
    public_key = serialization.load_pem_public_key(pem)
    ciphertext = public_key.encrypt(plaintext.encode("utf-8"), padding.PKCS1v15())
    return base64.b64encode(ciphertext).decode("utf-8")


def coerce_value(value: Any) -> Any:
    """Convert numeric strings and blank strings from the API."""
    if isinstance(value, str):
        stripped = value.strip()
        if stripped == "":
            return None
        try:
            if "." in stripped:
                return float(stripped)
            return int(stripped)
        except ValueError:
            return stripped
    return value


def _validate_settings_command_base(settings: Mapping[str, Any], serial: str) -> None:
    """Validate readback before using it as the base for a settings write."""
    missing = [
        field
        for field in SYSTEM_MODE_SETTING_FIELDS
        if field not in settings or settings[field] is None
    ]
    if missing:
        joined = ", ".join(missing)
        raise SunsynkUnsupportedSettingError(
            f"Sunsynk settings readback is missing required write fields: {joined}"
        )

    payload_serial = str(settings["sn"])
    if payload_serial != serial:
        raise SunsynkUnsupportedSettingError(
            f"Sunsynk settings serial {payload_serial} does not match inverter {serial}"
        )


def _coerce_setting_int(value: Any) -> int:
    """Coerce Sunsynk setting values that represent small integer enums."""
    if isinstance(value, bool):
        return 1 if value else 0
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in ("true", "on"):
            return 1
        if lowered in ("false", "off"):
            return 0
        try:
            return int(lowered)
        except ValueError as err:
            raise SunsynkUnsupportedSettingError(
                f"Sunsynk setting value {value!r} is not an integer"
            ) from err
    raise SunsynkUnsupportedSettingError(
        f"Sunsynk setting value {value!r} is not supported"
    )


def _empty_to_none(value: Any) -> str | None:
    """Return a string unless the value is blank or absent."""
    text = _string_or_none(value)
    return text if text else None


def _string_or_none(value: Any) -> str | None:
    """Return a string version of a value, preserving None."""
    if value is None:
        return None
    return str(value)
