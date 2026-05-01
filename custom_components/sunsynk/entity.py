"""Shared entity helpers for Sunsynk Cloud."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN
from .coordinator import SunsynkDataUpdateCoordinator


def build_device_info(coordinator: SunsynkDataUpdateCoordinator) -> DeviceInfo:
    """Build the Home Assistant device record."""
    inverter = coordinator.inverter
    detail = coordinator.data.detail if coordinator.data else {}
    version = detail.get("version") if isinstance(detail.get("version"), dict) else {}
    sw_parts = [
        version.get(key) for key in ("masterVer", "softVer", "hmiVer") if version.get(key)
    ]
    return DeviceInfo(
        identifiers={(DOMAIN, inverter.serial)},
        manufacturer="Sunsynk",
        name=inverter.name or f"Sunsynk {inverter.serial}",
        model=inverter.model or detail.get("model") or detail.get("type"),
        serial_number=inverter.serial,
        sw_version=" / ".join(sw_parts) if sw_parts else None,
    )
