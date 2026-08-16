"""Capability-limited read-only facade for the Huckleberry API client."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
import aiohttp
from huckleberry_api import HuckleberryAPI
from huckleberry_api.firebase_types import (
    FirebaseActivityDocumentData,
    FirebaseActivityIntervalData,
    FirebaseChildDocument,
    FirebaseDiaperData,
    FirebaseDiaperDocumentData,
    FirebaseFeedIntervalData,
    FirebaseFeedDocumentData,
    HealthDataEntry,
    FirebaseHealthDocumentData,
    FirebasePumpDocumentData,
    FirebasePumpIntervalData,
    FirebaseSleepIntervalData,
    FirebaseSleepDocumentData,
    FirebaseUserDocument,
)


class HuckleberryReadOnlyAPI:
    """Expose only audited authentication and Firestore read operations.

    The dependency also implements mutations. Composition keeps those methods
    unreachable from the Home Assistant integration, calendar, and entities.
    """

    __slots__ = ("__client",)

    def __init__(
        self,
        email: str,
        password: str,
        timezone: str,
        websession: aiohttp.ClientSession,
    ) -> None:
        self.__client = HuckleberryAPI(email, password, timezone, websession)

    @property
    def user_uid(self) -> str | None:
        """Return the authenticated Firebase user ID."""
        return self.__client.user_uid

    async def authenticate(self) -> None:
        """Authenticate without changing Huckleberry application data."""
        await self.__client.authenticate()

    async def ensure_session(self) -> None:
        """Refresh the authentication token when required."""
        await self.__client.ensure_session()

    async def get_user(self) -> FirebaseUserDocument | None:
        """Read the current user's document."""
        return await self.__client.get_user()

    async def get_child(self, child_uid: str) -> FirebaseChildDocument | None:
        """Read one child profile."""
        return await self.__client.get_child(child_uid)

    async def setup_sleep_listener(
        self, child_uid: str, callback: Callable[[FirebaseSleepDocumentData], None]
    ) -> None:
        await self.__client.setup_sleep_listener(child_uid, callback)

    async def setup_feed_listener(
        self, child_uid: str, callback: Callable[[FirebaseFeedDocumentData], None]
    ) -> None:
        await self.__client.setup_feed_listener(child_uid, callback)

    async def setup_health_listener(
        self, child_uid: str, callback: Callable[[FirebaseHealthDocumentData], None]
    ) -> None:
        await self.__client.setup_health_listener(child_uid, callback)

    async def setup_diaper_listener(
        self, child_uid: str, callback: Callable[[FirebaseDiaperDocumentData], None]
    ) -> None:
        await self.__client.setup_diaper_listener(child_uid, callback)

    async def setup_child_listener(
        self, child_uid: str, callback: Callable[[FirebaseChildDocument], None]
    ) -> None:
        await self.__client.setup_child_listener(child_uid, callback)

    async def setup_pump_listener(
        self, child_uid: str, callback: Callable[[FirebasePumpDocumentData], None]
    ) -> None:
        await self.__client.setup_pump_listener(child_uid, callback)

    async def setup_activity_listener(
        self, child_uid: str, callback: Callable[[FirebaseActivityDocumentData], None]
    ) -> None:
        await self.__client.setup_activity_listener(child_uid, callback)

    async def stop_all_listeners(self) -> None:
        """Release all read listeners."""
        await self.__client.stop_all_listeners()

    async def list_sleep_intervals(
        self, child_uid: str, start_time: datetime, end_time: datetime
    ) -> list[FirebaseSleepIntervalData]:
        return await self.__client.list_sleep_intervals(child_uid, start_time, end_time)

    async def list_feed_intervals(
        self, child_uid: str, start_time: datetime, end_time: datetime
    ) -> list[FirebaseFeedIntervalData]:
        return await self.__client.list_feed_intervals(child_uid, start_time, end_time)

    async def list_diaper_intervals(
        self, child_uid: str, start_time: datetime, end_time: datetime
    ) -> list[FirebaseDiaperData]:
        return await self.__client.list_diaper_intervals(
            child_uid, start_time, end_time
        )

    async def list_health_entries(
        self, child_uid: str, start_time: datetime, end_time: datetime
    ) -> list[HealthDataEntry]:
        return await self.__client.list_health_entries(child_uid, start_time, end_time)

    async def list_pump_intervals(
        self, child_uid: str, start_time: datetime, end_time: datetime
    ) -> list[FirebasePumpIntervalData]:
        return await self.__client.list_pump_intervals(child_uid, start_time, end_time)

    async def list_activity_intervals(
        self, child_uid: str, start_time: datetime, end_time: datetime
    ) -> list[FirebaseActivityIntervalData]:
        return await self.__client.list_activity_intervals(
            child_uid, start_time, end_time
        )
