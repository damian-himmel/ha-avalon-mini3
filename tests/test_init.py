"""Tests for setup, entities and commands."""

from __future__ import annotations

from unittest.mock import MagicMock

from freezegun.api import FrozenDateTimeFactory
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_time_changed

from custom_components.avalon_mini3.api import AvalonCommandError, AvalonConnectionError, WorkMode
from custom_components.avalon_mini3.const import SCAN_INTERVAL
from custom_components.avalon_mini3.diagnostics import async_get_config_entry_diagnostics
from homeassistant.components.button import SERVICE_PRESS
from homeassistant.components.select import ATTR_OPTION, SERVICE_SELECT_OPTION
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import ATTR_ENTITY_ID, SERVICE_TURN_OFF, STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from .conftest import load_data


async def test_setup_and_unload(hass: HomeAssistant, init_integration: MockConfigEntry) -> None:
    assert init_integration.state is ConfigEntryState.LOADED
    await hass.config_entries.async_unload(init_integration.entry_id)
    assert init_integration.state is ConfigEntryState.NOT_LOADED


async def test_setup_retry_when_offline(
    hass: HomeAssistant, mock_client: MagicMock, mock_config_entry: MockConfigEntry
) -> None:
    mock_client.async_get_data.side_effect = AvalonConnectionError
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    assert mock_config_entry.state is ConfigEntryState.SETUP_RETRY


@pytest.mark.parametrize(
    ("entity_id", "state"),
    [
        ("sensor.avalon_mini3_power", "750"),
        ("sensor.avalon_mini3_hashrate", "40.11"),
        ("sensor.avalon_mini3_inlet_temperature", "24.0"),
        ("sensor.avalon_mini3_fan_duty", "61"),
        ("sensor.avalon_mini3_pool", "stratum+tcp://eu3.solopool.org:8005"),
        ("sensor.avalon_mini3_network_difficulty", "140.58"),
        ("binary_sensor.avalon_mini3_pool_connected", "on"),
        ("select.avalon_mini3_work_mode", "mining"),
        ("switch.avalon_mini3_display", "on"),
    ],
)
async def test_entity_states(
    hass: HomeAssistant, init_integration: MockConfigEntry, entity_id: str, state: str
) -> None:
    assert hass.states.get(entity_id).state == state


async def test_unavailable_after_failed_poll(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    mock_client: MagicMock,
    freezer: FrozenDateTimeFactory,
) -> None:
    mock_client.async_get_data.side_effect = AvalonConnectionError
    freezer.tick(SCAN_INTERVAL)
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert hass.states.get("sensor.avalon_mini3_power").state == STATE_UNAVAILABLE


async def test_select_work_mode(
    hass: HomeAssistant, init_integration: MockConfigEntry, mock_client: MagicMock
) -> None:
    await hass.services.async_call(
        "select",
        SERVICE_SELECT_OPTION,
        {ATTR_ENTITY_ID: "select.avalon_mini3_work_mode", ATTR_OPTION: "heater_eco"},
        blocking=True,
    )
    mock_client.async_apply_work_mode.assert_awaited_once_with(WorkMode.HEATER_ECO, WorkMode.MINING)


async def test_display_off(
    hass: HomeAssistant, init_integration: MockConfigEntry, mock_client: MagicMock
) -> None:
    await hass.services.async_call(
        "switch",
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: "switch.avalon_mini3_display"},
        blocking=True,
    )
    mock_client.async_set_lcd.assert_awaited_once_with(False)


async def test_restart(
    hass: HomeAssistant, init_integration: MockConfigEntry, mock_client: MagicMock
) -> None:
    await hass.services.async_call(
        "button",
        SERVICE_PRESS,
        {ATTR_ENTITY_ID: "button.avalon_mini3_restart"},
        blocking=True,
    )
    mock_client.async_reboot.assert_awaited_once()


async def test_command_error(
    hass: HomeAssistant, init_integration: MockConfigEntry, mock_client: MagicMock
) -> None:
    mock_client.async_reboot.side_effect = AvalonCommandError("rejected")
    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            "button",
            SERVICE_PRESS,
            {ATTR_ENTITY_ID: "button.avalon_mini3_restart"},
            blocking=True,
        )


async def test_standby_state(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    mock_client: MagicMock,
    freezer: FrozenDateTimeFactory,
) -> None:
    mock_client.async_get_data.return_value = load_data(SYSTEMSTATU="Work: In Idle, Hash Board: 1")
    freezer.tick(SCAN_INTERVAL)
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert hass.states.get("select.avalon_mini3_work_mode").state == WorkMode.STANDBY


async def test_diagnostics_redacts_identifiers(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    result = await async_get_config_entry_diagnostics(hass, init_integration)
    assert result["data"]["version"]["MAC"] == "**REDACTED**"
    assert result["data"]["pools"][0]["User"] == "**REDACTED**"
    assert "DNA" not in result["data"]["mm"]
    assert result["data"]["mm"]["MPO"] == "750"
