"""Restart button of the Avalon Mini3."""

from __future__ import annotations

from homeassistant.components.button import ButtonDeviceClass, ButtonEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import AvalonConfigEntry, AvalonCoordinator
from .entity import AvalonEntity

PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AvalonConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the restart button."""
    async_add_entities([AvalonRestartButton(entry.runtime_data)])


class AvalonRestartButton(AvalonEntity, ButtonEntity):
    """Reboots the miner."""

    _attr_device_class = ButtonDeviceClass.RESTART
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: AvalonCoordinator) -> None:
        super().__init__(coordinator, "restart")

    async def async_press(self) -> None:
        await self._async_send(self.coordinator.client.async_reboot())
