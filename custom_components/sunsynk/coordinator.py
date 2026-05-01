"""Data coordinator for the Sunsynk Cloud integration."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta
import logging
from typing import Any

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import (
    SunsynkApiClient,
    SunsynkApiError,
    SunsynkInverter,
    SunsynkSample,
    SunsynkSettingsWriteError,
    build_settings_command_payload,
    setting_value_matches,
    normalize_monitoring_payloads,
    normalize_setting_update_value,
)
from .const import DOMAIN, SLOW_REFRESH_INTERVAL

_LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class SunsynkInverterData:
    """Latest data held by a Sunsynk inverter coordinator."""

    inverter: SunsynkInverter
    values: dict[str, SunsynkSample] = field(default_factory=dict)
    detail: dict[str, Any] = field(default_factory=dict)
    settings: dict[str, Any] = field(default_factory=dict)
    settings_supported: bool | None = None
    requested_at: datetime | None = None
    detail_refreshed_at: datetime | None = None
    settings_refreshed_at: datetime | None = None


class SunsynkDataUpdateCoordinator(DataUpdateCoordinator[SunsynkInverterData]):
    """Coordinate Sunsynk polling for one inverter."""

    def __init__(
        self,
        hass,
        api: SunsynkApiClient,
        inverter: SunsynkInverter,
        update_interval: timedelta,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{inverter.serial}",
            update_interval=update_interval,
        )
        self.api = api
        self.inverter = inverter
        self._settings_write_lock = asyncio.Lock()

    async def _async_update_data(self) -> SunsynkInverterData:
        """Fetch the latest data from Sunsynk Cloud."""
        previous = self.data or SunsynkInverterData(inverter=self.inverter)
        now = dt_util.now()
        refresh_slow = _is_stale(previous.detail_refreshed_at, SLOW_REFRESH_INTERVAL, now)
        refresh_settings = _is_stale(
            previous.settings_refreshed_at, SLOW_REFRESH_INTERVAL, now
        )

        fast_results = await asyncio.gather(
            self.api.async_get_realtime_input(self.inverter.serial),
            self.api.async_get_realtime_output(self.inverter.serial),
            self.api.async_get_realtime_grid(self.inverter.serial),
            self.api.async_get_realtime_battery(self.inverter.serial),
            self.api.async_get_realtime_load(self.inverter.serial),
            return_exceptions=True,
        )

        input_data, output_data, grid_data, battery_data, load_data = _unpack_results(
            fast_results
        )

        detail = previous.detail
        detail_refreshed_at = previous.detail_refreshed_at
        if refresh_slow:
            try:
                detail = await self.api.async_get_inverter_info(self.inverter.serial)
                detail_refreshed_at = now
            except SunsynkApiError as err:
                _LOGGER.debug(
                    "Unable to refresh Sunsynk inverter detail for %s: %s",
                    self.inverter.serial,
                    err,
                )

        settings = previous.settings
        settings_supported = previous.settings_supported
        settings_refreshed_at = previous.settings_refreshed_at
        if refresh_settings:
            try:
                settings = await self.api.async_get_settings(self.inverter.serial)
                settings_supported = True
                settings_refreshed_at = now
            except SunsynkApiError as err:
                settings_supported = False
                settings_refreshed_at = now
                _LOGGER.debug(
                    "Unable to refresh Sunsynk settings readback for %s: %s",
                    self.inverter.serial,
                    err,
                )

        values = normalize_monitoring_payloads(
            input_data=input_data,
            output_data=output_data,
            grid_data=grid_data,
            battery_data=battery_data,
            load_data=load_data,
            info_data=detail or self.inverter.raw,
        )
        if not values and not previous.values:
            raise UpdateFailed(f"No usable Sunsynk data for {self.inverter.serial}")
        if not values:
            values = previous.values

        return SunsynkInverterData(
            inverter=self.inverter,
            values=values,
            detail=detail,
            settings=settings,
            settings_supported=settings_supported,
            requested_at=now,
            detail_refreshed_at=detail_refreshed_at,
            settings_refreshed_at=settings_refreshed_at,
        )

    async def async_set_setting(self, setting_key: str, value: Any) -> None:
        """Write one supported setting and confirm it by immediate readback."""
        expected_value = normalize_setting_update_value(setting_key, value)

        async with self._settings_write_lock:
            settings = await self.api.async_get_settings(self.inverter.serial)
            payload = build_settings_command_payload(
                settings,
                self.inverter.serial,
                {setting_key: expected_value},
            )
            await self.api.async_set_settings(self.inverter.serial, payload)
            confirmed = await self.api.async_get_settings(self.inverter.serial)

            if not setting_value_matches(confirmed, setting_key, expected_value):
                raise SunsynkSettingsWriteError(
                    f"Sunsynk did not confirm {setting_key}={expected_value}"
                )

            self._update_settings_data(confirmed)

    def _update_settings_data(self, settings: dict[str, Any]) -> None:
        """Publish fresh settings without forcing a full realtime refresh."""
        current = self.data or SunsynkInverterData(inverter=self.inverter)
        self.async_set_updated_data(
            replace(
                current,
                settings=settings,
                settings_supported=True,
                settings_refreshed_at=dt_util.now(),
            )
        )


def _unpack_results(results: list[Any]) -> tuple[dict[str, Any], ...]:
    """Convert gathered endpoint results into dictionaries while logging failures."""
    payloads: list[dict[str, Any]] = []
    for result in results:
        if isinstance(result, Exception):
            _LOGGER.debug("Sunsynk endpoint refresh failed: %s", result)
            payloads.append({})
        elif isinstance(result, dict):
            payloads.append(result)
        else:
            payloads.append({})
    return tuple(payloads)  # type: ignore[return-value]


def _is_stale(
    last_refreshed_at: datetime | None,
    interval: timedelta,
    now: datetime,
) -> bool:
    """Return whether an occasionally refreshed payload should be refreshed."""
    return last_refreshed_at is None or now - last_refreshed_at >= interval
