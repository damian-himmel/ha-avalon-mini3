"""Display switch of the Avalon Mini3."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
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
    """Set up the display switch."""
    async_add_entities([AvalonDisplaySwitch(entry.runtime_data)])


class AvalonDisplaySwitch(AvalonEntity, SwitchEntity):
    """Turns the LCD on or off."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_translation_key = "display"

    def __init__(self, coordinator: AvalonCoordinator) -> None:
        super().__init__(coordinator, "display")

    @property
    def is_on(self) -> bool | None:
        value = self.coordinator.data.mm_int("LcdOnoff")
        return None if value is None else value == 1

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._async_send(self.coordinator.client.async_set_lcd(True))

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._async_send(self.coordinator.client.async_set_lcd(False))
