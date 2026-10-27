# Avalon Mini3 for Home Assistant

🇬🇧 **English** · 🇩🇪 [Deutsch](README_DE.md)

Local integration for the **Canaan Avalon Mini3** bitcoin miner / space heater. It talks to the
miner's CGMiner API on TCP port 4028 – no cloud, no account.

## Features

- **Work mode** select: Standby, Heater eco, Heater super, Mining, Night. Leaving standby wakes
  the miner automatically.
- **Display** switch and **Restart** button
- Sensors for power, hashrate, inlet/outlet/hashboard/chip temperatures, fan speed and duty,
  pool, accepted/rejected shares, best share, found blocks and network difficulty
- Diagnostic sensors for uptime, system status, hardware errors, pool ping and chip frequency
- Pool connectivity binary sensor
- The miner is identified by its MAC address. If its IP address changes, add it again or use
  *Reconfigure* – entities and history stay.

Tested with firmware `25022401_cb28ba7`.

## Installation

### HACS

1. HACS → ⋮ → *Custom repositories* → add `https://github.com/damian-himmel/ha-avalon-mini3`
   with category *Integration*.
2. Install **Avalon Mini3** and restart Home Assistant.

### Manual

Copy `custom_components/avalon_mini3` into the `custom_components` folder of your Home Assistant
configuration and restart.

## Setup

*Settings → Devices & services → Add integration → Avalon Mini3*, then enter the IP address of
the miner. Reserve a fixed address for it in your router.

## Notes

- Commands take about two seconds until the miner reports the new state.
- Polling interval is 15 seconds.

## Credits

The structure was inspired by [avalon_nano3s](https://github.com/jinx-22/avalon_nano3s) by
@jinx-22.

## Trademarks

Avalon and the Avalon logo are trademarks of Canaan Inc. This project is not affiliated with or
endorsed by Canaan.

## License

[MIT](LICENSE)
