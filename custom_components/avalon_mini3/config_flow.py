"""Config flow for the Avalon Mini3."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.device_registry import format_mac

from .api import DEFAULT_PORT, AvalonConnectionError, AvalonError, AvalonMini3Client
from .const import DOMAIN, SUPPORTED_MODEL

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_PORT, default=DEFAULT_PORT): cv.port,
    }
)


async def _async_probe(user_input: dict[str, Any]) -> tuple[dict[str, Any], dict[str, str]]:
    """Read the version response; return it together with form errors."""
    client = AvalonMini3Client(user_input[CONF_HOST], user_input[CONF_PORT])
    try:
        version = await client.async_get_version()
    except AvalonConnectionError:
        return {}, {"base": "cannot_connect"}
    except AvalonError:
        return {}, {"base": "invalid_response"}
    if not version.get("MAC"):
        return {}, {"base": "invalid_response"}
    if version.get("MODEL") != SUPPORTED_MODEL:
        return {}, {"base": "unsupported_model"}
    return version, {}


class AvalonMini3ConfigFlow(ConfigFlow, domain=DOMAIN):
    """Adds a miner by host; the MAC address identifies it across IP changes."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            version, errors = await _async_probe(user_input)
            if not errors:
                await self.async_set_unique_id(format_mac(version["MAC"]))
                # Adding a known miner again only updates its address.
                self._abort_if_unique_id_configured(updates=user_input)
                return self.async_create_entry(
                    title=version.get("PROD") or "Avalon Mini3", data=user_input
                )
        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(DATA_SCHEMA, user_input),
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            version, errors = await _async_probe(user_input)
            if not errors:
                await self.async_set_unique_id(format_mac(version["MAC"]))
                self._abort_if_unique_id_mismatch(reason="wrong_device")
                return self.async_update_reload_and_abort(entry, data_updates=user_input)
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(DATA_SCHEMA, user_input or entry.data),
            errors=errors,
        )
