"""Sensor platform for Sunsynk Cloud."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfFrequency,
    UnitOfPower,
    UnitOfTemperature,
)
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import SunsynkSample
from .const import DOMAIN
from .coordinator import SunsynkDataUpdateCoordinator


@dataclass(frozen=True, kw_only=True)
class SunsynkSensorDescription(SensorEntityDescription):
    """Description of a Sunsynk sensor."""

    value_key: str


SENSOR_DESCRIPTIONS: tuple[SunsynkSensorDescription, ...] = (
    SunsynkSensorDescription(
        key="solar_power",
        value_key="solar_power",
        name="Solar Power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:solar-power",
    ),
    SunsynkSensorDescription(
        key="solar_energy_today",
        value_key="solar_energy_today",
        name="Solar Energy Today",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:solar-power",
    ),
    SunsynkSensorDescription(
        key="solar_energy_total",
        value_key="solar_energy_total",
        name="Solar Energy Total",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:solar-power-variant",
    ),
    SunsynkSensorDescription(
        key="grid_power",
        value_key="grid_power",
        name="Grid Power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:transmission-tower",
    ),
    SunsynkSensorDescription(
        key="grid_import_today",
        value_key="grid_import_today",
        name="Grid Import Today",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:transmission-tower-import",
    ),
    SunsynkSensorDescription(
        key="grid_export_today",
        value_key="grid_export_today",
        name="Grid Export Today",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:transmission-tower-export",
    ),
    SunsynkSensorDescription(
        key="grid_import_total",
        value_key="grid_import_total",
        name="Grid Import Total",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:transmission-tower-import",
    ),
    SunsynkSensorDescription(
        key="grid_export_total",
        value_key="grid_export_total",
        name="Grid Export Total",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:transmission-tower-export",
    ),
    SunsynkSensorDescription(
        key="load_power",
        value_key="load_power",
        name="Load Power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:home-lightning-bolt",
    ),
    SunsynkSensorDescription(
        key="load_energy_today",
        value_key="load_energy_today",
        name="Load Energy Today",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:home-lightning-bolt",
    ),
    SunsynkSensorDescription(
        key="load_energy_total",
        value_key="load_energy_total",
        name="Load Energy Total",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:home-lightning-bolt-outline",
    ),
    SunsynkSensorDescription(
        key="battery_soc",
        value_key="battery_soc",
        name="Battery SOC",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SunsynkSensorDescription(
        key="battery_power",
        value_key="battery_power",
        name="Battery Power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:battery-sync",
    ),
    SunsynkSensorDescription(
        key="battery_voltage",
        value_key="battery_voltage",
        name="Battery Voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SunsynkSensorDescription(
        key="battery_current",
        value_key="battery_current",
        name="Battery Current",
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SunsynkSensorDescription(
        key="battery_temperature",
        value_key="battery_temperature",
        name="Battery Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SunsynkSensorDescription(
        key="battery_charge_today",
        value_key="battery_charge_today",
        name="Battery Charge Today",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:battery-arrow-up",
    ),
    SunsynkSensorDescription(
        key="battery_discharge_today",
        value_key="battery_discharge_today",
        name="Battery Discharge Today",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:battery-arrow-down",
    ),
    SunsynkSensorDescription(
        key="battery_charge_total",
        value_key="battery_charge_total",
        name="Battery Charge Total",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:battery-arrow-up-outline",
    ),
    SunsynkSensorDescription(
        key="battery_discharge_total",
        value_key="battery_discharge_total",
        name="Battery Discharge Total",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:battery-arrow-down-outline",
    ),
    SunsynkSensorDescription(
        key="inverter_power",
        value_key="inverter_power",
        name="Inverter Power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:sine-wave",
    ),
    SunsynkSensorDescription(
        key="inverter_frequency",
        value_key="inverter_frequency",
        name="Inverter Frequency",
        device_class=SensorDeviceClass.FREQUENCY,
        native_unit_of_measurement=UnitOfFrequency.HERTZ,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SunsynkSensorDescription(
        key="inverter_rated_power",
        value_key="inverter_rated_power",
        name="Inverter Rated Power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
)


async def async_setup_entry(hass, entry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up Sunsynk sensors."""
    runtime_data = hass.data[DOMAIN][entry.entry_id]
    coordinators: dict[str, SunsynkDataUpdateCoordinator] = runtime_data["coordinators"]

    entities: list[SensorEntity] = []
    for coordinator in coordinators.values():
        coordinator_entities, seen_keys = _build_entities_for_coordinator(coordinator)
        entities.extend(coordinator_entities)
        _register_dynamic_entity_addition(
            entry,
            coordinator,
            seen_keys,
            async_add_entities,
        )

    async_add_entities(entities)


def _build_entities_for_coordinator(
    coordinator: SunsynkDataUpdateCoordinator,
) -> tuple[list[SensorEntity], set[str]]:
    """Build entities for one inverter coordinator."""
    entities: list[SensorEntity] = [
        SunsynkAPICallsTodaySensor(coordinator),
        SunsynkSettingsReadbackSensor(coordinator),
    ]

    seen_keys: set[str] = set()
    for description in SENSOR_DESCRIPTIONS:
        entities.append(SunsynkCloudSensor(coordinator, description))
        seen_keys.add(description.value_key)

    for key, sample in coordinator.data.values.items():
        if key in seen_keys:
            continue
        entities.append(SunsynkCloudSensor(coordinator, _dynamic_description(key, sample)))
        seen_keys.add(key)

    return entities, seen_keys


def _register_dynamic_entity_addition(
    entry,
    coordinator: SunsynkDataUpdateCoordinator,
    seen_keys: set[str],
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add newly discovered normalized samples after the first refresh."""

    def _handle_coordinator_update() -> None:
        new_entities: list[SensorEntity] = []
        for key, sample in coordinator.data.values.items():
            if key in seen_keys:
                continue
            seen_keys.add(key)
            new_entities.append(
                SunsynkCloudSensor(coordinator, _dynamic_description(key, sample))
            )
        if new_entities:
            async_add_entities(new_entities)

    entry.async_on_unload(coordinator.async_add_listener(_handle_coordinator_update))


class SunsynkCloudSensor(CoordinatorEntity[SunsynkDataUpdateCoordinator], SensorEntity):
    """Representation of a Sunsynk sensor."""

    entity_description: SunsynkSensorDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: SunsynkDataUpdateCoordinator,
        description: SunsynkSensorDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.inverter.serial}_{description.key}"
        self._attr_device_info = build_device_info(coordinator)
        self._attr_name = description.name
        self._attr_entity_registry_enabled_default = (
            description.entity_registry_enabled_default
        )

    @property
    def available(self) -> bool:
        """Return whether the sensor currently has a value."""
        return super().available and self._sample is not None

    @property
    def native_value(self) -> Any:
        """Return the native value."""
        sample = self._sample
        return sample.value if sample is not None else None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Expose source details for diagnostics."""
        sample = self._sample
        if sample is None:
            return None
        attributes: dict[str, Any] = {
            "api_source": sample.source,
            "api_key": sample.raw_key,
        }
        if sample.updated_at:
            attributes["data_updated_at"] = sample.updated_at
        return attributes

    @property
    def _sample(self) -> SunsynkSample | None:
        """Return the current sample for this entity."""
        return self.coordinator.data.values.get(self.entity_description.value_key)


class SunsynkAPICallsTodaySensor(
    CoordinatorEntity[SunsynkDataUpdateCoordinator], SensorEntity
):
    """Diagnostic sensor showing daily API calls for one inverter."""

    _attr_has_entity_name = True
    _attr_name = "API Calls Today"
    _attr_icon = "mdi:counter"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: SunsynkDataUpdateCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.inverter.serial}_api_calls_today"
        self._attr_device_info = build_device_info(coordinator)

    @property
    def native_value(self) -> int:
        """Return today's API call count."""
        return self.coordinator.api.get_daily_usage(self.coordinator.inverter.serial).calls

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return diagnostic API usage details."""
        usage = self.coordinator.api.get_daily_usage(self.coordinator.inverter.serial)
        return {
            "date": usage.day.isoformat(),
            "api_errors_today": usage.errors,
            "last_api_call": usage.last_called_at,
            "last_api_error": usage.last_error_at,
        }


class SunsynkSettingsReadbackSensor(
    CoordinatorEntity[SunsynkDataUpdateCoordinator], SensorEntity
):
    """Diagnostic sensor showing whether settings readback is available."""

    _attr_has_entity_name = True
    _attr_name = "Settings Readback"
    _attr_icon = "mdi:cog-search"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: SunsynkDataUpdateCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.inverter.serial}_settings_readback"
        self._attr_device_info = build_device_info(coordinator)

    @property
    def native_value(self) -> str | None:
        """Return settings readback support state."""
        supported = self.coordinator.data.settings_supported
        if supported is True:
            return "available"
        if supported is False:
            return "unavailable"
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return settings readback metadata."""
        settings = self.coordinator.data.settings
        return {
            "settings_refreshed_at": self.coordinator.data.settings_refreshed_at,
            "setting_count": len(settings),
            "writable_candidates": _known_writable_candidates(settings),
        }


def build_device_info(coordinator: SunsynkDataUpdateCoordinator) -> DeviceInfo:
    """Build the Home Assistant device record."""
    inverter = coordinator.inverter
    detail = coordinator.data.detail if coordinator.data else {}
    version = detail.get("version") if isinstance(detail.get("version"), dict) else {}
    sw_parts = [version.get(key) for key in ("masterVer", "softVer", "hmiVer") if version.get(key)]
    return DeviceInfo(
        identifiers={(DOMAIN, inverter.serial)},
        manufacturer="Sunsynk",
        name=inverter.name or f"Sunsynk {inverter.serial}",
        model=inverter.model or detail.get("model") or detail.get("type"),
        serial_number=inverter.serial,
        sw_version=" / ".join(sw_parts) if sw_parts else None,
    )


def _dynamic_description(key: str, sample: SunsynkSample) -> SunsynkSensorDescription:
    """Build a description for a normalized value discovered at runtime."""
    kwargs: dict[str, Any] = {
        "key": key,
        "value_key": key,
        "name": sample.name,
    }

    if sample.unit == "W":
        kwargs.update(
            device_class=SensorDeviceClass.POWER,
            native_unit_of_measurement=UnitOfPower.WATT,
            state_class=SensorStateClass.MEASUREMENT,
        )
    elif sample.unit == "kWh":
        kwargs.update(
            device_class=SensorDeviceClass.ENERGY,
            native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
            state_class=SensorStateClass.TOTAL_INCREASING,
        )
    elif sample.unit == "V":
        kwargs.update(
            device_class=SensorDeviceClass.VOLTAGE,
            native_unit_of_measurement=UnitOfElectricPotential.VOLT,
            state_class=SensorStateClass.MEASUREMENT,
        )
    elif sample.unit == "A":
        kwargs.update(
            device_class=SensorDeviceClass.CURRENT,
            native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
            state_class=SensorStateClass.MEASUREMENT,
        )
    elif sample.unit == "Hz":
        kwargs.update(
            device_class=SensorDeviceClass.FREQUENCY,
            native_unit_of_measurement=UnitOfFrequency.HERTZ,
            state_class=SensorStateClass.MEASUREMENT,
        )
    elif sample.unit == "C":
        kwargs.update(
            device_class=SensorDeviceClass.TEMPERATURE,
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            state_class=SensorStateClass.MEASUREMENT,
        )
    elif sample.unit == "%":
        kwargs.update(
            native_unit_of_measurement=PERCENTAGE,
            state_class=SensorStateClass.MEASUREMENT,
        )

    return SunsynkSensorDescription(**kwargs)


def _known_writable_candidates(settings: dict[str, Any]) -> list[str]:
    """Return documented candidate write keys found in settings readback."""
    candidates = {
        "sysWorkMode",
        "energyMode",
        "solarSell",
        "pvMaxLimit",
        "zeroExportPower",
        "solarMaxSellPower",
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
        "cap1",
        "cap2",
        "cap3",
        "cap4",
        "cap5",
        "cap6",
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
        "batteryLowCap",
        "batteryShutdownCap",
        "batteryRestartCap",
        "batteryMaxCurrentCharge",
        "batteryMaxCurrentDischarge",
    }
    return sorted(key for key in candidates if key in settings)
