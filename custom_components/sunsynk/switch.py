"""Switch platform for Sunsynk Cloud writable settings."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import (
    SunsynkApiError,
    normalize_setting_update_value,
    setting_update_supported,
)
from .const import DOMAIN
from .coordinator import SunsynkDataUpdateCoordinator
from .entity import build_device_info


@dataclass(frozen=True, kw_only=True)
class SunsynkSwitchDescription(SwitchEntityDescription):
    """Description of a Sunsynk switch entity."""

    setting_key: str


SWITCH_DESCRIPTIONS: tuple[SunsynkSwitchDescription, ...] = (
    SunsynkSwitchDescription(
        key="system_timer",
        setting_key="peakAndVallery",
        name="System Timer",
        icon="mdi:timer-cog",
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=True,
    ),
)


async def async_setup_entry(hass, entry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up Sunsynk switch entities."""
    runtime_data = hass.data[DOMAIN][entry.entry_id]
    coordinators: dict[str, SunsynkDataUpdateCoordinator] = runtime_data["coordinators"]

    entities: list[SwitchEntity] = []
    for coordinator in coordinators.values():
        for description in SWITCH_DESCRIPTIONS:
            entities.append(SunsynkSettingsSwitch(coordinator, description))

    async_add_entities(entities)


class SunsynkSettingsSwitch(
    CoordinatorEntity[SunsynkDataUpdateCoordinator], SwitchEntity
):
    """Representation of a Sunsynk settings switch."""

    entity_description: SunsynkSwitchDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: SunsynkDataUpdateCoordinator,
        description: SunsynkSwitchDescription,
    ) -> None:
        """Initialize the switch entity."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.inverter.serial}_{description.key}"
        self._attr_device_info = build_device_info(coordinator)
        self._attr_name = description.name
        self._attr_entity_category = description.entity_category
        self._attr_entity_registry_enabled_default = (
            description.entity_registry_enabled_default
        )

    @property
    def available(self) -> bool:
        """Return whether this switch can currently be used."""
        return (
            super().available
            and self.coordinator.data.settings_supported is True
            and setting_update_supported(
                self.coordinator.data.settings,
                self.coordinator.inverter.serial,
                self.entity_description.setting_key,
            )
            and self.is_on is not None
        )

    @property
    def is_on(self) -> bool | None:
        """Return the timer state from settings readback."""
        value = _current_setting_value(
            self.coordinator.data.settings,
            self.entity_description.setting_key,
        )
        if value is None:
            return None
        return value == 1

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return settings write diagnostics."""
        return {
            "setting_key": self.entity_description.setting_key,
            "settings_readback": self.coordinator.data.settings_supported,
            "write_payload_supported": setting_update_supported(
                self.coordinator.data.settings,
                self.coordinator.inverter.serial,
                self.entity_description.setting_key,
            ),
        }

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable the Sunsynk setting."""
        await self._async_set_switch_value(1)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable the Sunsynk setting."""
        await self._async_set_switch_value(0)

    async def _async_set_switch_value(self, value: int) -> None:
        """Set the switch-backed Sunsynk setting value."""
        try:
            await self.coordinator.async_set_setting(
                self.entity_description.setting_key,
                value,
            )
        except SunsynkApiError as err:
            raise HomeAssistantError(f"Unable to update Sunsynk setting: {err}") from err


def _current_setting_value(settings: dict[str, Any], setting_key: str) -> int | None:
    """Return a normalized current setting value, if the value is supported."""
    if setting_key not in settings:
        return None
    try:
        return normalize_setting_update_value(setting_key, settings[setting_key])
    except SunsynkApiError:
        return None
