"""Constants for the Avalon Mini3 integration."""

from datetime import timedelta
import logging
from typing import Final

DOMAIN: Final = "avalon_mini3"
LOGGER = logging.getLogger(__package__)

SCAN_INTERVAL: Final = timedelta(seconds=15)

# Value of "MODEL" in the version response of supported devices.
SUPPORTED_MODEL: Final = "Mini3"
