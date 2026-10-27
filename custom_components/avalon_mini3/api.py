"""Async client for the CGMiner API of the Canaan Avalon Mini3."""

from __future__ import annotations

import asyncio
from contextlib import suppress
from dataclasses import dataclass
from enum import StrEnum
import json
import re
import time
from typing import Any

DEFAULT_PORT = 4028
DEFAULT_TIMEOUT = 5.0

# Seconds the miner needs to apply a setting before the next command or poll.
DEFAULT_COMMAND_DELAY = 2.0

# The "MM ID0" string of the stats response packs most values as `Key[value]`,
# e.g. `ITemp[24]` or `SYSTEMSTATU[Work: In Work, Hash Board: 1]`.
_MM_FIELD = re.compile(r"(\w+)\[([^\]]*)\]")


class AvalonError(Exception):
    """Base error of the Avalon Mini3 client."""


class AvalonConnectionError(AvalonError):
    """The miner could not be reached."""


class AvalonCommandError(AvalonError):
    """The miner answered with an error or an unreadable response."""


class WorkMode(StrEnum):
    """Operating modes offered by the Avalon Mini3."""

    STANDBY = "standby"
    HEATER_ECO = "heater_eco"
    HEATER_SUPER = "heater_super"
    MINING = "mining"
    NIGHT = "night"


# (workmode, worklevel) sent for each active mode; worklevel is only used by the heater.
_MODE_SETTINGS: dict[WorkMode, tuple[int, int | None]] = {
    WorkMode.HEATER_ECO: (0, -1),
    WorkMode.HEATER_SUPER: (0, 0),
    WorkMode.MINING: (1, None),
    WorkMode.NIGHT: (2, None),
}


def parse_mm(text: str) -> dict[str, str]:
    """Split the "MM ID0" string into a dict of raw string values."""
    return {key: value.strip() for key, value in _MM_FIELD.findall(text)}


def _first(response: dict[str, Any], key: str) -> dict[str, Any]:
    items = response.get(key)
    if not isinstance(items, list) or not items or not isinstance(items[0], dict):
        raise AvalonCommandError(f"Response has no {key} section")
    return items[0]


@dataclass(frozen=True)
class AvalonData:
    """One snapshot of everything the integration reads from the miner."""

    version: dict[str, Any]
    summary: dict[str, Any]
    mm: dict[str, str]
    pools: list[dict[str, Any]]
    coin: dict[str, Any]

    @classmethod
    def from_responses(
        cls,
        version: dict[str, Any],
        summary: dict[str, Any],
        stats: dict[str, Any],
        pools: dict[str, Any],
        coin: dict[str, Any],
    ) -> AvalonData:
        """Build a snapshot from the raw API responses."""
        return cls(
            version=_first(version, "VERSION"),
            summary=_first(summary, "SUMMARY"),
            mm=parse_mm(_first(stats, "STATS").get("MM ID0", "")),
            pools=[pool for pool in pools.get("POOLS", []) if isinstance(pool, dict)],
            coin=(coin.get("COIN") or [{}])[0],
        )

    def mm_float(self, key: str) -> float | None:
        """Return a numeric "MM ID0" value, ignoring a trailing unit such as "%"."""
        try:
            return float(self.mm[key].rstrip("%"))
        except KeyError, ValueError:
            return None

    def mm_int(self, key: str) -> int | None:
        """Return a "MM ID0" value as integer."""
        value = self.mm_float(key)
        return None if value is None else int(value)

    @property
    def active_pool(self) -> dict[str, Any] | None:
        """Return the pool the miner currently works for."""
        for pool in self.pools:
            if pool.get("Stratum Active"):
                return pool
        return self.pools[0] if self.pools else None

    @property
    def work_mode(self) -> WorkMode | None:
        """Derive the operating mode from system status, workmode and worklevel."""
        status = self.mm.get("SYSTEMSTATU", "")
        if "In Idle" in status:
            return WorkMode.STANDBY
        if "In Work" not in status:
            return None
        mode = self.mm_int("WORKMODE")
        if mode == 0:
            level = self.mm_int("WORKLEVEL") or 0
            return WorkMode.HEATER_ECO if level < 0 else WorkMode.HEATER_SUPER
        return {1: WorkMode.MINING, 2: WorkMode.NIGHT}.get(mode)  # type: ignore[arg-type]


class AvalonMini3Client:
    """Talks to the CGMiner JSON API (TCP port 4028) of one miner."""

    def __init__(
        self,
        host: str,
        port: int = DEFAULT_PORT,
        timeout: float = DEFAULT_TIMEOUT,
        command_delay: float = DEFAULT_COMMAND_DELAY,
    ) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout
        self.command_delay = command_delay
        # The miner answers one request per connection; overlapping
        # connections from polling and commands are serialized.
        self._lock = asyncio.Lock()

    async def _request(self, command: str, parameter: str | None = None) -> dict[str, Any]:
        payload: dict[str, str] = {"command": command}
        if parameter is not None:
            payload["parameter"] = parameter

        async with self._lock:
            try:
                async with asyncio.timeout(self.timeout):
                    reader, writer = await asyncio.open_connection(self.host, self.port)
                    try:
                        writer.write(json.dumps(payload).encode())
                        await writer.drain()
                        raw = await reader.read()
                    finally:
                        writer.close()
                        with suppress(OSError):
                            await writer.wait_closed()
            except (TimeoutError, OSError) as err:
                raise AvalonConnectionError(
                    f"Cannot reach the miner at {self.host}:{self.port}"
                ) from err

        # Every response is terminated by a NUL byte.
        try:
            response = json.loads(raw.rstrip(b"\x00").decode())
        except (UnicodeDecodeError, ValueError) as err:
            raise AvalonCommandError(f"Unreadable response to {command!r}") from err
        if not isinstance(response, dict):
            raise AvalonCommandError(f"Unexpected response to {command!r}")

        # "S" = success of a query, "I" = info, which ascset returns on success.
        status = _first(response, "STATUS")
        if status.get("STATUS") not in ("S", "I"):
            raise AvalonCommandError(f"{command!r} failed: {status.get('Msg', 'unknown error')}")
        return response

    async def async_get_version(self) -> dict[str, Any]:
        """Return model, firmware and MAC address."""
        return _first(await self._request("version"), "VERSION")

    async def async_get_data(self) -> AvalonData:
        """Read a complete snapshot."""
        return AvalonData.from_responses(
            version=await self._request("version"),
            summary=await self._request("summary"),
            stats=await self._request("stats"),
            pools=await self._request("pools"),
            coin=await self._request("coin"),
        )

    async def _ascset(self, parameter: str) -> None:
        await self._request("ascset", f"0,{parameter}")

    async def async_set_work_mode(self, mode: int) -> None:
        """Set workmode (0 = heater, 1 = mining, 2 = night)."""
        await self._ascset(f"workmode,set,{mode}")

    async def async_set_work_level(self, level: int) -> None:
        """Set the heater level (0 = super, -1 = eco)."""
        await self._ascset(f"worklevel,set,{level}")

    async def async_standby(self) -> None:
        """Put the miner into standby."""
        await self._ascset(f"softoff,1:{self._soft_timestamp()}")

    async def async_wake(self) -> None:
        """Wake the miner from standby."""
        await self._ascset(f"softon,1:{self._soft_timestamp()}")

    async def async_set_lcd(self, on: bool) -> None:
        """Switch the display on or off."""
        await self._ascset(f"lcd,0:{int(on)}")

    async def async_reboot(self) -> None:
        """Restart the miner."""
        await self._ascset("reboot,0")

    async def async_apply_work_mode(self, target: WorkMode, current: WorkMode | None) -> None:
        """Switch to a mode, waking the miner first if it is in standby."""
        if target is WorkMode.STANDBY:
            await self.async_standby()
            return

        if current is WorkMode.STANDBY:
            await self.async_wake()
            await asyncio.sleep(self.command_delay)

        mode, level = _MODE_SETTINGS[target]
        await self.async_set_work_mode(mode)
        if level is not None:
            await asyncio.sleep(self.command_delay)
            await self.async_set_work_level(level)

    @staticmethod
    def _soft_timestamp() -> int:
        # softoff/softon expect a Unix timestamp; now + 60 s is accepted reliably.
        return int(time.time()) + 60
