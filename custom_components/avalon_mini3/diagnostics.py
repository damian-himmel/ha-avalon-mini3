"""Diagnostics for the Avalon Mini3, attached to bug reports."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from .coordinator import AvalonConfigEntry

TO_REDACT = {"MAC", "DNA", "User", "unique_id"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: AvalonConfigEntry
) -> dict[str, Any]:
    """Return the latest snapshot without identifying data."""
    data = asdict(entry.runtime_data.data)
    data["mm"].pop("DNA", None)
    return async_redact_data(
        {"entry": entry.as_dict(), "data": data},
        TO_REDACT,
    )
