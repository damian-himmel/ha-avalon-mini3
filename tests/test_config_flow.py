"""Tests for the config flow."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.avalon_mini3.api import AvalonCommandError, AvalonConnectionError
from custom_components.avalon_mini3.const import DOMAIN
from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from .conftest import HOST, MAC, load_data

USER_INPUT = {CONF_HOST: HOST, CONF_PORT: 4028}


async def test_user_flow(hass: HomeAssistant, mock_client: MagicMock) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert result["type"] is FlowResultType.FORM

    result = await hass.config_entries.flow.async_configure(result["flow_id"], USER_INPUT)
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Avalon Mini3"
    assert result["data"] == USER_INPUT
    assert result["result"].unique_id == MAC


@pytest.mark.parametrize(
    ("side_effect", "version", "error"),
    [
        (AvalonConnectionError, None, "cannot_connect"),
        (AvalonCommandError, None, "invalid_response"),
        (
            None,
            {"PROD": "Avalon Nano3s", "MODEL": "Nano3s", "MAC": "001122334455"},
            "unsupported_model",
        ),
        (None, {"PROD": "Avalon Mini3", "MODEL": "Mini3"}, "invalid_response"),
    ],
)
async def test_user_flow_errors(
    hass: HomeAssistant,
    mock_client: MagicMock,
    side_effect: type[Exception] | None,
    version: dict | None,
    error: str,
) -> None:
    mock_client.async_get_version.side_effect = side_effect
    if version is not None:
        mock_client.async_get_version.return_value = version
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], USER_INPUT)
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": error}

    # The form recovers once the miner answers correctly.
    mock_client.async_get_version.side_effect = None
    mock_client.async_get_version.return_value = load_data().version
    result = await hass.config_entries.flow.async_configure(result["flow_id"], USER_INPUT)
    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_known_miner_updates_host(
    hass: HomeAssistant, mock_client: MagicMock, mock_config_entry: MockConfigEntry
) -> None:
    mock_config_entry.add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: "192.0.2.99", CONF_PORT: 4028}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert mock_config_entry.data[CONF_HOST] == "192.0.2.99"


async def test_reconfigure(
    hass: HomeAssistant, mock_client: MagicMock, init_integration: MockConfigEntry
) -> None:
    result = await init_integration.start_reconfigure_flow(hass)
    assert result["type"] is FlowResultType.FORM

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: "192.0.2.42", CONF_PORT: 4028}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert init_integration.data[CONF_HOST] == "192.0.2.42"


async def test_reconfigure_other_miner(
    hass: HomeAssistant, mock_client: MagicMock, init_integration: MockConfigEntry
) -> None:
    mock_client.async_get_version.return_value = {
        **load_data().version,
        "MAC": "ffeeddccbbaa",
    }
    result = await init_integration.start_reconfigure_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: "192.0.2.42", CONF_PORT: 4028}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "wrong_device"
    assert init_integration.data[CONF_HOST] == HOST
