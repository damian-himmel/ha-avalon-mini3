"""Binary sensors of the Avalon Mini3."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import AvalonConfigEntry, AvalonCoordinator
from .entity import AvalonEntity

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AvalonConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the binary sensors."""
    async_add_entities([AvalonPoolConnected(entry.runtime_data)])


class AvalonPoolConnected(AvalonEntity, BinarySensorEntity):
    """Whether the active pool is alive."""

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_translation_key = "pool_connected"

    def __init__(self, coordinator: AvalonCoordinator) -> None:
        super().__init__(coordinator, "pool_connected")

    @property
    def is_on(self) -> bool | None:
        pool = self.coordinator.data.active_pool
        return None if pool is None else pool.get("Status") == "Alive"
