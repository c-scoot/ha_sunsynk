"""Config flow for Sunsynk Cloud."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import (
    SunsynkApiClient,
    SunsynkApiError,
    SunsynkAuthenticationError,
    SunsynkCannotConnectError,
)
from .const import (
    CONF_API_BASE_URL,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
    DEFAULT_API_BASE_URL,
    DEFAULT_SCAN_INTERVAL_SECONDS,
    DOMAIN,
    MIN_SCAN_INTERVAL_SECONDS,
)


class SunsynkConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a Sunsynk Cloud config flow."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.FlowResult:
        """Handle the initial user step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            session = async_get_clientsession(self.hass)
            client = SunsynkApiClient(
                session,
                user_input[CONF_USERNAME],
                user_input[CONF_PASSWORD],
                base_url=user_input[CONF_API_BASE_URL],
            )

            try:
                inverters = await client.async_list_inverters()
            except SunsynkAuthenticationError:
                errors["base"] = "invalid_auth"
            except SunsynkCannotConnectError:
                errors["base"] = "cannot_connect"
            except SunsynkApiError:
                errors["base"] = "unknown"
            else:
                if not inverters:
                    errors["base"] = "no_inverters"
                else:
                    await self.async_set_unique_id(user_input[CONF_USERNAME].lower())
                    self._abort_if_unique_id_configured()
                    title = _entry_title(inverters)
                    return self.async_create_entry(title=title, data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=_user_schema(user_input),
            errors=errors,
        )

    @staticmethod
    def async_get_options_flow(config_entry):
        """Return the options flow handler."""
        return SunsynkOptionsFlow(config_entry)


class SunsynkOptionsFlow(config_entries.OptionsFlow):
    """Handle Sunsynk options."""

    def __init__(self, config_entry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.FlowResult:
        """Manage Sunsynk options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_interval = self._config_entry.options.get(
            CONF_SCAN_INTERVAL,
            self._config_entry.data.get(
                CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL_SECONDS
            ),
        )
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SCAN_INTERVAL,
                        default=current_interval,
                    ): vol.All(
                        vol.Coerce(int), vol.Range(min=MIN_SCAN_INTERVAL_SECONDS)
                    ),
                }
            ),
        )


def _user_schema(user_input: dict[str, Any] | None) -> vol.Schema:
    """Return the setup form schema."""
    user_input = user_input or {}
    return vol.Schema(
        {
            vol.Required(
                CONF_USERNAME,
                default=user_input.get(CONF_USERNAME, ""),
            ): str,
            vol.Required(CONF_PASSWORD): str,
            vol.Optional(
                CONF_API_BASE_URL,
                default=user_input.get(CONF_API_BASE_URL, DEFAULT_API_BASE_URL),
            ): str,
            vol.Optional(
                CONF_SCAN_INTERVAL,
                default=user_input.get(
                    CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL_SECONDS
                ),
            ): vol.All(vol.Coerce(int), vol.Range(min=MIN_SCAN_INTERVAL_SECONDS)),
        }
    )


def _entry_title(inverters: list[Any]) -> str:
    """Build a friendly title for the config entry."""
    if len(inverters) == 1:
        inverter = inverters[0]
        return inverter.name or f"Sunsynk {inverter.serial}"
    return "Sunsynk Cloud"
