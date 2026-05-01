"""Select platform for Sunsynk Cloud writable settings."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from homeassistant.components.select import SelectEntity, SelectEntityDescription
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
class SunsynkSelectDescription(SelectEntityDescription):
    """Description of a Sunsynk select entity."""

    setting_key: str
    options_by_value: Mapping[int, str]


SELECT_DESCRIPTIONS: tuple[SunsynkSelectDescription, ...] = (
    SunsynkSelectDescription(
        key="system_work_mode",
        setting_key="sysWorkMode",
        name="System Work Mode",
        options_by_value={
            0: "Selling First",
            1: "Zero-Export + Limited to Load",
            2: "Limited to Home",
        },
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
    ),
    SunsynkSelectDescription(
        key="energy_pattern",
        setting_key="energyMode",
        name="Energy Pattern",
        options_by_value={
            0: "Priority Battery",
            1: "Priority Load",
        },
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
    ),
)


async def async_setup_entry(hass, entry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up Sunsynk select entities."""
    runtime_data = hass.data[DOMAIN][entry.entry_id]
    coordinators: dict[str, SunsynkDataUpdateCoordinator] = runtime_data["coordinators"]

    entities: list[SelectEntity] = []
    for coordinator in coordinators.values():
        for description in SELECT_DESCRIPTIONS:
            if setting_update_supported(
                coordinator.data.settings,
                coordinator.inverter.serial,
                description.setting_key,
            ):
                entities.append(SunsynkSettingsSelect(coordinator, description))

    async_add_entities(entities)


class SunsynkSettingsSelect(
    CoordinatorEntity[SunsynkDataUpdateCoordinator], SelectEntity
):
    """Representation of a Sunsynk settings select."""

    entity_description: SunsynkSelectDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: SunsynkDataUpdateCoordinator,
        description: SunsynkSelectDescription,
    ) -> None:
        """Initialize the select entity."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.inverter.serial}_{description.key}"
        self._attr_device_info = build_device_info(coordinator)
        self._attr_name = description.name
        self._attr_entity_category = description.entity_category
        self._attr_entity_registry_enabled_default = (
            description.entity_registry_enabled_default
        )
        self._option_to_value = {
            option: value for value, option in description.options_by_value.items()
        }

    @property
    def available(self) -> bool:
        """Return whether this select can currently be used."""
        return (
            super().available
            and self.coordinator.data.settings_supported is True
            and setting_update_supported(
                self.coordinator.data.settings,
                self.coordinator.inverter.serial,
                self.entity_description.setting_key,
            )
            and self.current_option is not None
        )

    @property
    def options(self) -> list[str]:
        """Return selectable option labels."""
        return list(self.entity_description.options_by_value.values())

    @property
    def current_option(self) -> str | None:
        """Return the current option from settings readback."""
        value = _current_setting_value(
            self.coordinator.data.settings,
            self.entity_description.setting_key,
        )
        if value is None:
            return None
        return self.entity_description.options_by_value.get(value)

    async def async_select_option(self, option: str) -> None:
        """Set the selected Sunsynk setting value."""
        if option not in self._option_to_value:
            raise HomeAssistantError(f"Unsupported Sunsynk option: {option}")
        try:
            await self.coordinator.async_set_setting(
                self.entity_description.setting_key,
                self._option_to_value[option],
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
