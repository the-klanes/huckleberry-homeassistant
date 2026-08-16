"""Configuration flow for read-only Huckleberry access."""

from __future__ import annotations

from typing import Any

import aiohttp
from google.api_core.exceptions import GoogleAPICallError
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from pydantic import ValidationError

from . import async_load_children
from .api import HuckleberryReadOnlyAPI
from .const import DOMAIN


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Collect credentials and prove read access."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                api = HuckleberryReadOnlyAPI(
                    user_input[CONF_EMAIL],
                    user_input[CONF_PASSWORD],
                    str(self.hass.config.time_zone),
                    async_get_clientsession(self.hass),
                )
                await api.authenticate()
                children = await async_load_children(api)
                if not children:
                    errors["base"] = "no_children"
                else:
                    await self.async_set_unique_id(api.user_uid)
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(
                        title="Huckleberry (Read-only)", data=user_input
                    )
            except aiohttp.ClientResponseError as err:
                errors["base"] = (
                    "invalid_auth" if err.status == 400 else "cannot_connect"
                )
            except (
                aiohttp.ClientConnectionError,
                aiohttp.ServerTimeoutError,
                GoogleAPICallError,
                ValidationError,
            ):
                errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_EMAIL): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
        )
