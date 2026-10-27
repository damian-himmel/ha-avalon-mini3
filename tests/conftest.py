"""Shared fixtures."""

from __future__ import annotations

from collections.abc import Generator
import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.avalon_mini3.api import AvalonData, AvalonMini3Client
from custom_components.avalon_mini3.const import DOMAIN
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant

FIXTURES = Path(__file__).parent / "fixtures"
HOST = "192.0.2.10"
MAC = "0a:1b:2c:3d:4e:5f"


def load_response(command: str) -> dict[str, Any]:
    """Load a recorded (anonymized) API response."""
    return json.loads((FIXTURES / f"{command}.json").read_text())


def load_data(**mm_overrides: str) -> AvalonData:
    """Build a snapshot from the recorded responses, optionally changing MM fields."""
    data = AvalonData.from_responses(
        version=load_response("version"),
        summary=load_response("summary"),
        stats=load_response("stats"),
        pools=load_response("pools"),
        coin=load_response("coin"),
    )
    data.mm.update(mm_overrides)
    return data


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Allow loading the integration from custom_components."""


@pytest.fixture
def mock_client() -> Generator[MagicMock]:
    """Replace the API client everywhere it is created."""
    client = MagicMock(spec=AvalonMini3Client)
    client.host = HOST
    client.command_delay = 0
    client.async_get_version = AsyncMock(return_value=load_data().version)
    client.async_get_data = AsyncMock(return_value=load_data())
    with (
        patch("custom_components.avalon_mini3.AvalonMini3Client", return_value=client),
        patch(
            "custom_components.avalon_mini3.config_flow.AvalonMini3Client",
            return_value=client,
        ),
    ):
        yield client


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """A configured miner."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Avalon Mini3",
        unique_id=MAC,
        data={CONF_HOST: HOST, CONF_PORT: 4028},
    )


@pytest.fixture
async def init_integration(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_client: MagicMock
) -> MockConfigEntry:
    """Set up the integration with the recorded snapshot."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    return mock_config_entry
