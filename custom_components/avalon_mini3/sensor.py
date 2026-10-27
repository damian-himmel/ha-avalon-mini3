"""Sensors of the Avalon Mini3."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    REVOLUTIONS_PER_MINUTE,
    EntityCategory,
    UnitOfFrequency,
    UnitOfPower,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.typing import StateType

from .api import AvalonData
from .coordinator import AvalonConfigEntry, AvalonCoordinator
from .entity import AvalonEntity

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class AvalonSensorEntityDescription(SensorEntityDescription):
    """Sensor description with a function reading the value from a snapshot."""

    value_fn: Callable[[AvalonData], StateType]


def _terahash(data: AvalonData, key: str) -> float | None:
    value = data.mm_float(key)
    return None if value is None else round(value / 1000, 2)


def _pool_value(data: AvalonData, key: str) -> StateType:
    pool = data.active_pool
    return None if pool is None else pool.get(key)


def _network_difficulty(data: AvalonData) -> float | None:
    value = data.coin.get("Network Difficulty")
    return None if value is None else round(value / 1e12, 2)


def _temperature(key: str, translation_key: str) -> AvalonSensorEntityDescription:
    return AvalonSensorEntityDescription(
        key=translation_key,
        translation_key=translation_key,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda data: data.mm_float(key),
    )


SENSORS: tuple[AvalonSensorEntityDescription, ...] = (
    AvalonSensorEntityDescription(
        key="power",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        value_fn=lambda data: data.mm_int("MPO"),
    ),
    AvalonSensorEntityDescription(
        key="hashrate",
        translation_key="hashrate",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="TH/s",
        suggested_display_precision=2,
        value_fn=lambda data: _terahash(data, "GHSspd"),
    ),
    AvalonSensorEntityDescription(
        key="hashrate_average",
        translation_key="hashrate_average",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="TH/s",
        suggested_display_precision=2,
        value_fn=lambda data: _terahash(data, "GHSavg"),
    ),
    _temperature("ITemp", "temperature_inlet"),
    _temperature("OTemp", "temperature_outlet"),
    _temperature("HBTemp", "temperature_hashboard"),
    _temperature("TMax", "temperature_chip_max"),
    _temperature("TAvg", "temperature_chip_average"),
    AvalonSensorEntityDescription(
        key="fan_speed",
        translation_key="fan_speed",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=REVOLUTIONS_PER_MINUTE,
        value_fn=lambda data: data.mm_int("Fan1"),
    ),
    AvalonSensorEntityDescription(
        key="fan_duty",
        translation_key="fan_duty",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        value_fn=lambda data: data.mm_int("FanR"),
    ),
    AvalonSensorEntityDescription(
        key="pool",
        translation_key="pool",
        value_fn=lambda data: _pool_value(data, "URL"),
    ),
    AvalonSensorEntityDescription(
        key="accepted_shares",
        translation_key="accepted_shares",
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda data: data.summary.get("Accepted"),
    ),
    AvalonSensorEntityDescription(
        key="rejected_shares",
        translation_key="rejected_shares",
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda data: data.summary.get("Rejected"),
    ),
    AvalonSensorEntityDescription(
        key="best_share",
        translation_key="best_share",
        value_fn=lambda data: data.summary.get("Best Share"),
    ),
    AvalonSensorEntityDescription(
        key="found_blocks",
        translation_key="found_blocks",
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda data: data.summary.get("Found Blocks"),
    ),
    AvalonSensorEntityDescription(
        key="network_difficulty",
        translation_key="network_difficulty",
        native_unit_of_measurement="T",
        value_fn=_network_difficulty,
    ),
    AvalonSensorEntityDescription(
        key="hardware_errors",
        translation_key="hardware_errors",
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda data: data.summary.get("Hardware Errors"),
    ),
    AvalonSensorEntityDescription(
        key="uptime",
        translation_key="uptime",
        device_class=SensorDeviceClass.DURATION,
        entity_category=EntityCategory.DIAGNOSTIC,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        suggested_unit_of_measurement=UnitOfTime.HOURS,
        suggested_display_precision=1,
        value_fn=lambda data: data.mm_int("Elapsed"),
    ),
    AvalonSensorEntityDescription(
        key="system_status",
        translation_key="system_status",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.mm.get("SYSTEMSTATU"),
    ),
    AvalonSensorEntityDescription(
        key="pool_ping",
        translation_key="pool_ping",
        device_class=SensorDeviceClass.DURATION,
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTime.MILLISECONDS,
        value_fn=lambda data: data.mm_int("PING"),
    ),
    AvalonSensorEntityDescription(
        key="chip_frequency",
        translation_key="chip_frequency",
        device_class=SensorDeviceClass.FREQUENCY,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfFrequency.MEGAHERTZ,
        value_fn=lambda data: data.mm_float("Freq"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AvalonConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the sensors."""
    coordinator = entry.runtime_data
    async_add_entities(AvalonSensor(coordinator, description) for description in SENSORS)


class AvalonSensor(AvalonEntity, SensorEntity):
    """A value read from the miner."""

    entity_description: AvalonSensorEntityDescription

    def __init__(
        self, coordinator: AvalonCoordinator, description: AvalonSensorEntityDescription
    ) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> StateType:
        return self.entity_description.value_fn(self.coordinator.data)
