"""The Sunsynk Cloud integration."""

from __future__ import annotations

from datetime import timedelta

from .const import (
    CONF_API_BASE_URL,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
    DEFAULT_SCAN_INTERVAL_SECONDS,
    DOMAIN,
    MIN_SCAN_INTERVAL_SECONDS,
)


async def async_setup_entry(hass, entry) -> bool:
    """Set up Sunsynk Cloud from a config entry."""
    from homeassistant.const import Platform
    from homeassistant.exceptions import ConfigEntryNotReady
    from homeassistant.helpers.aiohttp_client import async_get_clientsession

    from .api import SunsynkApiClient, SunsynkApiError
    from .coordinator import SunsynkDataUpdateCoordinator

    session = async_get_clientsession(hass)
    api = SunsynkApiClient(
        session,
        entry.data[CONF_USERNAME],
        entry.data[CONF_PASSWORD],
        base_url=entry.data[CONF_API_BASE_URL],
    )

    try:
        inverters = await api.async_list_inverters()
    except SunsynkApiError as err:
        raise ConfigEntryNotReady(f"Unable to connect to Sunsynk Cloud: {err}") from err

    if not inverters:
        raise ConfigEntryNotReady("No Sunsynk inverters were returned for this account")

    interval_seconds = max(
        MIN_SCAN_INTERVAL_SECONDS,
        int(
            entry.options.get(
                CONF_SCAN_INTERVAL,
                entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL_SECONDS),
            )
        ),
    )
    interval = timedelta(seconds=interval_seconds)
    coordinators: dict[str, SunsynkDataUpdateCoordinator] = {}
    for inverter in inverters:
        coordinator = SunsynkDataUpdateCoordinator(hass, api, inverter, interval)
        await coordinator.async_config_entry_first_refresh()
        coordinators[inverter.serial] = coordinator

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "api": api,
        "coordinators": coordinators,
    }

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    await hass.config_entries.async_forward_entry_setups(entry, (Platform.SENSOR,))
    return True


async def async_unload_entry(hass, entry) -> bool:
    """Unload a Sunsynk Cloud config entry."""
    from homeassistant.const import Platform

    unload_ok = await hass.config_entries.async_unload_platforms(entry, (Platform.SENSOR,))
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


async def _async_update_listener(hass, entry) -> None:
    """Reload the entry when options change."""
    await hass.config_entries.async_reload(entry.entry_id)
