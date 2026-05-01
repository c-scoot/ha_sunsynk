"""Constants for the Sunsynk Cloud integration."""

from __future__ import annotations

from datetime import timedelta

DOMAIN = "sunsynk"

CONF_API_BASE_URL = "api_base_url"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"

DEFAULT_API_BASE_URL = "https://api.sunsynk.net"
DEFAULT_SCAN_INTERVAL_SECONDS = 60
MIN_SCAN_INTERVAL_SECONDS = 60
SLOW_REFRESH_INTERVAL = timedelta(hours=6)
