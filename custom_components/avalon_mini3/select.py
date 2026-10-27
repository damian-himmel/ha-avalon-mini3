"""Work mode select of the Avalon Mini3."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .api import WorkMode
from .coordinator import AvalonConfigEntry, AvalonCoordinator
from .entity import AvalonEntity

PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AvalonConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the work mode select."""
    async_add_entities([AvalonWorkModeSelect(entry.runtime_data)])


class AvalonWorkModeSelect(AvalonEntity, SelectEntity):
    """Standby, heater (eco/super), mining or night mode."""

    _attr_options = [mode.value for mode in WorkMode]
    _attr_translation_key = "work_mode"

    def __init__(self, coordinator: AvalonCoordinator) -> None:
        super().__init__(coordinator, "work_mode")

    @property
    def current_option(self) -> str | None:
        mode = self.coordinator.data.work_mode
        return None if mode is None else mode.value

    async def async_select_option(self, option: str) -> None:
        await self._async_send(
            self.coordinator.client.async_apply_work_mode(
                WorkMode(option), self.coordinator.data.work_mode
            )
        )
