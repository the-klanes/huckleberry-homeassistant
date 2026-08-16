"""Strictly read-only Huckleberry integration for Home Assistant."""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import TypedDict, cast

import aiohttp
from aiohttp import ClientError
from google.api_core.exceptions import GoogleAPICallError
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from huckleberry_api.firebase_types import (
    FirebaseActivityDocumentData,
    FirebaseChildDocument,
    FirebaseDiaperDocumentData,
    FirebaseFeedDocumentData,
    FirebaseHealthDocumentData,
    FirebasePumpDocumentData,
    FirebaseSleepDocumentData,
    FirebaseUserDocument,
)
from pydantic import ValidationError

from .api import HuckleberryReadOnlyAPI
from .const import DOMAIN, PLATFORMS
from .models import HuckleberryChildProfile, HuckleberryChildState

_LOGGER = logging.getLogger(__name__)


class HuckleberryEntryData(TypedDict):
    """Runtime data for one config entry."""

    api: HuckleberryReadOnlyAPI
    coordinator: "HuckleberryDataUpdateCoordinator"
    children: list[HuckleberryChildProfile]


async def _async_load_child_profiles(
    api: HuckleberryReadOnlyAPI, user: FirebaseUserDocument
) -> list[HuckleberryChildProfile]:
    documents = await asyncio.gather(
        *(api.get_child(ref.cid) for ref in user.childList)
    )
    return [
        HuckleberryChildProfile(uid=ref.cid, reference=ref, document=document)
        for ref, document in zip(user.childList, documents, strict=True)
        if document is not None
    ]


async def async_load_children(
    api: HuckleberryReadOnlyAPI,
) -> list[HuckleberryChildProfile]:
    """Read and resolve all child profiles for the authenticated account."""
    user = await api.get_user()
    return [] if user is None else await _async_load_child_profiles(api, user)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up sensors and calendar; never register controls or services."""
    api = HuckleberryReadOnlyAPI(
        entry.data["email"],
        entry.data["password"],
        str(hass.config.time_zone),
        async_get_clientsession(hass),
    )
    try:
        await api.authenticate()
        children = await async_load_children(api)
    except aiohttp.ClientResponseError as err:
        if err.status == 400:
            raise ConfigEntryAuthFailed("Huckleberry rejected the credentials") from err
        raise ConfigEntryNotReady("Huckleberry authentication is unavailable") from err
    except (ClientError, GoogleAPICallError, ValidationError) as err:
        raise ConfigEntryNotReady(
            "Huckleberry data is temporarily unavailable"
        ) from err

    if not children:
        raise ConfigEntryNotReady("No Huckleberry child profiles were available")

    coordinator = HuckleberryDataUpdateCoordinator(hass, api, children)
    await coordinator.async_config_entry_first_refresh()
    try:
        await coordinator.async_setup_listeners()
    except (ClientError, GoogleAPICallError, ValidationError, RuntimeError) as err:
        await coordinator.async_shutdown()
        raise ConfigEntryNotReady("Huckleberry listeners could not start") from err

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = HuckleberryEntryData(
        api=api, coordinator=coordinator, children=children
    )
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload the config entry and its read listeners."""
    entry_data = cast(
        HuckleberryEntryData | None, hass.data.get(DOMAIN, {}).get(entry.entry_id)
    )
    if entry_data is not None:
        await entry_data["coordinator"].async_shutdown()
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok


class HuckleberryDataUpdateCoordinator(
    DataUpdateCoordinator[dict[str, HuckleberryChildState]]
):
    """Maintain authentication and realtime read-only state."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: HuckleberryReadOnlyAPI,
        children: list[HuckleberryChildProfile],
    ) -> None:
        self.api = api
        self.children = children
        self._realtime_data = {
            child.uid: HuckleberryChildState(profile=child) for child in children
        }
        super().__init__(
            hass, _LOGGER, name=DOMAIN, update_interval=timedelta(minutes=15)
        )

    def _publish(self) -> None:
        """Notify coordinator entities after applying one validated document."""
        self.async_set_updated_data(dict(self._realtime_data))

    def _apply_sleep(self, child_uid: str, data: FirebaseSleepDocumentData) -> None:
        self._realtime_data[child_uid].sleep_status = data
        self._publish()

    def _apply_feed(self, child_uid: str, data: FirebaseFeedDocumentData) -> None:
        self._realtime_data[child_uid].feed_status = data
        self._publish()

    def _apply_health(self, child_uid: str, data: FirebaseHealthDocumentData) -> None:
        self._realtime_data[child_uid].health_status = data
        self._publish()

    def _apply_diaper(self, child_uid: str, data: FirebaseDiaperDocumentData) -> None:
        self._realtime_data[child_uid].diaper_status = data
        self._publish()

    def _apply_profile(self, child_uid: str, data: FirebaseChildDocument) -> None:
        self._realtime_data[child_uid].child_document = data
        self._publish()

    def _apply_pump(self, child_uid: str, data: FirebasePumpDocumentData) -> None:
        self._realtime_data[child_uid].pump_status = data
        self._publish()

    def _apply_activity(
        self, child_uid: str, data: FirebaseActivityDocumentData
    ) -> None:
        self._realtime_data[child_uid].activity_status = data
        self._publish()

    async def async_setup_listeners(self) -> None:
        """Subscribe to the seven audited read-only document streams."""
        for child in self.children:
            uid = child.uid

            def sleep(data: FirebaseSleepDocumentData, child_uid: str = uid) -> None:
                self.hass.loop.call_soon_threadsafe(self._apply_sleep, child_uid, data)

            def feed(data: FirebaseFeedDocumentData, child_uid: str = uid) -> None:
                self.hass.loop.call_soon_threadsafe(self._apply_feed, child_uid, data)

            def health(data: FirebaseHealthDocumentData, child_uid: str = uid) -> None:
                self.hass.loop.call_soon_threadsafe(self._apply_health, child_uid, data)

            def diaper(data: FirebaseDiaperDocumentData, child_uid: str = uid) -> None:
                self.hass.loop.call_soon_threadsafe(self._apply_diaper, child_uid, data)

            def profile(data: FirebaseChildDocument, child_uid: str = uid) -> None:
                self.hass.loop.call_soon_threadsafe(
                    self._apply_profile, child_uid, data
                )

            def pump(data: FirebasePumpDocumentData, child_uid: str = uid) -> None:
                self.hass.loop.call_soon_threadsafe(self._apply_pump, child_uid, data)

            def activity(
                data: FirebaseActivityDocumentData, child_uid: str = uid
            ) -> None:
                self.hass.loop.call_soon_threadsafe(
                    self._apply_activity, child_uid, data
                )

            await self.api.setup_sleep_listener(uid, sleep)
            await self.api.setup_feed_listener(uid, feed)
            await self.api.setup_health_listener(uid, health)
            await self.api.setup_diaper_listener(uid, diaper)
            await self.api.setup_child_listener(uid, profile)
            await self.api.setup_pump_listener(uid, pump)
            await self.api.setup_activity_listener(uid, activity)

    async def _async_update_data(self) -> dict[str, HuckleberryChildState]:
        try:
            await self.api.ensure_session()
        except (ClientError, ValueError) as err:
            raise UpdateFailed("Huckleberry session refresh failed") from err
        return dict(self._realtime_data)

    async def async_shutdown(self) -> None:
        await self.api.stop_all_listeners()

    def get_state(self, child_uid: str) -> HuckleberryChildState | None:
        return self.data.get(child_uid)

    def get_sleep_status(self, child_uid: str) -> FirebaseSleepDocumentData | None:
        state = self.get_state(child_uid)
        return None if state is None else state.sleep_status

    def get_feed_status(self, child_uid: str) -> FirebaseFeedDocumentData | None:
        state = self.get_state(child_uid)
        return None if state is None else state.feed_status

    def get_health_status(self, child_uid: str) -> FirebaseHealthDocumentData | None:
        state = self.get_state(child_uid)
        return None if state is None else state.health_status

    def get_diaper_status(self, child_uid: str) -> FirebaseDiaperDocumentData | None:
        state = self.get_state(child_uid)
        return None if state is None else state.diaper_status

    def get_pump_status(self, child_uid: str) -> FirebasePumpDocumentData | None:
        state = self.get_state(child_uid)
        return None if state is None else state.pump_status

    def get_activity_status(
        self, child_uid: str
    ) -> FirebaseActivityDocumentData | None:
        state = self.get_state(child_uid)
        return None if state is None else state.activity_status
