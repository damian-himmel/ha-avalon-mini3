"""Tests for the API client, independent of Home Assistant."""

from __future__ import annotations

from collections.abc import Generator
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.avalon_mini3.api import (
    AvalonCommandError,
    AvalonConnectionError,
    AvalonMini3Client,
    WorkMode,
    parse_mm,
)

from .conftest import load_data, load_response


@pytest.fixture
def fake_miner() -> Generator[tuple[AvalonMini3Client, list[dict]]]:
    """Answer like the miner (NUL-terminated) without opening real sockets."""
    received: list[dict] = []
    replies: dict[str, bytes] = {
        command: json.dumps(load_response(command)).encode() + b"\x00"
        for command in ("version", "summary", "stats", "pools", "coin")
    }
    replies["ascset"] = (
        b'{"STATUS":[{"STATUS":"I","Code":118,"Msg":"ASC 0 set info: success"}],"id":1}\x00'
    )
    replies["broken"] = b'{"STATUS":[{"STATUS":"E","Code":14,"Msg":"Invalid command"}],"id":1}\x00'

    async def open_connection(host: str, port: int) -> tuple[MagicMock, MagicMock]:
        writer = MagicMock()
        writer.drain = AsyncMock()
        writer.wait_closed = AsyncMock()
        reader = MagicMock()

        async def read() -> bytes:
            request = json.loads(writer.write.call_args.args[0])
            received.append(request)
            return replies[request["command"]]

        reader.read = read
        return reader, writer

    with patch("asyncio.open_connection", open_connection):
        yield AvalonMini3Client("192.0.2.10", command_delay=0), received


def test_parse_mm() -> None:
    mm = parse_mm("ITemp[24] SYSTEMSTATU[Work: In Work, Hash Board: 1] WORKLEVEL[-1] FanR[60%]")
    assert mm == {
        "ITemp": "24",
        "SYSTEMSTATU": "Work: In Work, Hash Board: 1",
        "WORKLEVEL": "-1",
        "FanR": "60%",
    }


def test_snapshot_values() -> None:
    data = load_data()
    assert data.mm_int("MPO") == 750
    assert data.mm_int("FanR") == 61
    assert data.mm_float("GHSspd") == pytest.approx(40114.38)
    assert data.mm_int("missing") is None
    assert data.active_pool is not None
    assert data.active_pool["Stratum Active"] is True


@pytest.mark.parametrize(
    ("status", "mode", "level", "expected"),
    [
        ("Work: In Idle, Hash Board: 1", "1", "0", WorkMode.STANDBY),
        ("Work: In Work, Hash Board: 1", "0", "-1", WorkMode.HEATER_ECO),
        ("Work: In Work, Hash Board: 1", "0", "0", WorkMode.HEATER_SUPER),
        ("Work: In Work, Hash Board: 1", "1", "0", WorkMode.MINING),
        ("Work: In Work, Hash Board: 1", "2", "0", WorkMode.NIGHT),
        ("Work: In Work, Hash Board: 1", "7", "0", None),
        ("Booting", "1", "0", None),
    ],
)
def test_work_mode(status: str, mode: str, level: str, expected: WorkMode | None) -> None:
    data = load_data(SYSTEMSTATU=status, WORKMODE=mode, WORKLEVEL=level)
    assert data.work_mode is expected


async def test_get_data(fake_miner: tuple[AvalonMini3Client, list[dict]]) -> None:
    client, received = fake_miner
    data = await client.async_get_data()
    assert data.version["MODEL"] == "Mini3"
    assert data.mm["SYSTEMSTATU"].startswith("Work: In Work")
    assert [request["command"] for request in received] == [
        "version",
        "summary",
        "stats",
        "pools",
        "coin",
    ]


async def test_ascset_parameter(fake_miner: tuple[AvalonMini3Client, list[dict]]) -> None:
    client, received = fake_miner
    await client.async_set_lcd(False)
    assert received == [{"command": "ascset", "parameter": "0,lcd,0:0"}]


async def test_error_status(fake_miner: tuple[AvalonMini3Client, list[dict]]) -> None:
    client, _ = fake_miner
    with pytest.raises(AvalonCommandError, match="Invalid command"):
        await client._request("broken")


async def test_unreachable() -> None:
    with (
        patch("asyncio.open_connection", AsyncMock(side_effect=ConnectionRefusedError)),
        pytest.raises(AvalonConnectionError),
    ):
        await AvalonMini3Client("192.0.2.10").async_get_version()


async def test_timeout(fake_miner: tuple[AvalonMini3Client, list[dict]]) -> None:
    client, _ = fake_miner
    with (
        patch("asyncio.open_connection", AsyncMock(side_effect=TimeoutError)),
        pytest.raises(AvalonConnectionError),
    ):
        await client.async_get_version()


def _client_with_mocked_commands() -> AvalonMini3Client:
    client = AvalonMini3Client("127.0.0.1", command_delay=0)
    client._ascset = AsyncMock()  # type: ignore[method-assign]
    return client


@pytest.mark.parametrize(
    ("target", "current", "expected"),
    [
        (WorkMode.STANDBY, WorkMode.MINING, ["softoff"]),
        (WorkMode.MINING, WorkMode.HEATER_ECO, ["workmode,set,1"]),
        (WorkMode.NIGHT, WorkMode.STANDBY, ["softon", "workmode,set,2"]),
        (WorkMode.HEATER_ECO, WorkMode.MINING, ["workmode,set,0", "worklevel,set,-1"]),
        (
            WorkMode.HEATER_SUPER,
            WorkMode.STANDBY,
            ["softon", "workmode,set,0", "worklevel,set,0"],
        ),
    ],
)
async def test_apply_work_mode(target: WorkMode, current: WorkMode, expected: list[str]) -> None:
    client = _client_with_mocked_commands()
    await client.async_apply_work_mode(target, current)
    sent = [args[0] for args, _ in client._ascset.call_args_list]  # type: ignore[attr-defined]
    assert [parameter.split(",1:")[0] for parameter in sent] == expected
    assert client._ascset.call_count == len(expected)  # type: ignore[attr-defined]
