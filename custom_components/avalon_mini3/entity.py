"""Base entity for the Avalon Mini3."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable

from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import AvalonError
from .const import DOMAIN
from .coordinator import AvalonCoordinator


class AvalonEntity(CoordinatorEntity[AvalonCoordinator]):
    """Entity bound to one miner, identified by its MAC address."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: AvalonCoordinator, key: str) -> None:
        super().__init__(coordinator)
        mac = coordinator.config_entry.unique_id
        assert mac is not None
        version = coordinator.data.version
        self._attr_unique_id = f"{mac}_{key}"
        self._attr_device_info = DeviceInfo(
            connections={(CONNECTION_NETWORK_MAC, mac)},
            identifiers={(DOMAIN, mac)},
            manufacturer="Canaan",
            name=version.get("PROD") or "Avalon Mini3",
            model=version.get("PROD"),
            model_id=version.get("MODEL"),
            hw_version=version.get("HWTYPE"),
            sw_version=version.get("LVERSION"),
            configuration_url=f"http://{coordinator.client.host}",
        )

    async def _async_send(self, command: Awaitable[None]) -> None:
        """Run a command, then refresh once the miner has applied it."""
        try:
            await command
        except AvalonError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="command_failed",
                translation_placeholders={"error": str(err)},
            ) from err
        await asyncio.sleep(self.coordinator.client.command_delay)
        await self.coordinator.async_request_refresh()
