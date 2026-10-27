"""Polling coordinator for the Avalon Mini3."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import AvalonData, AvalonError, AvalonMini3Client
from .const import DOMAIN, LOGGER, SCAN_INTERVAL

type AvalonConfigEntry = ConfigEntry[AvalonCoordinator]


class AvalonCoordinator(DataUpdateCoordinator[AvalonData]):
    """Fetches a snapshot from the miner every SCAN_INTERVAL."""

    config_entry: AvalonConfigEntry

    def __init__(
        self, hass: HomeAssistant, entry: AvalonConfigEntry, client: AvalonMini3Client
    ) -> None:
        super().__init__(
            hass,
            LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
        )
        self.client = client

    async def _async_update_data(self) -> AvalonData:
        try:
            return await self.client.async_get_data()
        except AvalonError as err:
            raise UpdateFailed(str(err)) from err
