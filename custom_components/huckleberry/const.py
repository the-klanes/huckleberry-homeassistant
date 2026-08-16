"""Constants for the read-only Huckleberry integration."""

from typing import Final

from homeassistant.const import Platform

DOMAIN: Final = "huckleberry"
PLATFORMS: Final[list[Platform]] = [Platform.SENSOR, Platform.CALENDAR]
