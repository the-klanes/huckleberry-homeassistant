"""Read-only Huckleberry sensor platform."""

from __future__ import annotations

from datetime import datetime

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from huckleberry_api.firebase_types import (
    FirebaseLastActivityData,
    FirebaseLastBottleData,
    FirebaseLastDiaperData,
    FirebaseLastPottyData,
    FirebaseLastPumpData,
    FirebaseLastSolidData,
    FirebaseMedicationData,
    FirebaseTemperatureData,
)

from . import HuckleberryDataUpdateCoordinator, HuckleberryEntryData
from .const import DOMAIN
from .entity import HuckleberryBaseEntity
from .models import HuckleberryChildProfile
from .timestamps import as_datetime, as_iso8601_datetime, as_iso8601_duration


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Create observation-only entities."""
    data: HuckleberryEntryData = hass.data[DOMAIN][entry.entry_id]
    entities: list[SensorEntity] = []
    for child in data["children"]:
        entities.extend(
            (
                HuckleberrySleepSensor(data["coordinator"], child),
                HuckleberryNursingSensor(data["coordinator"], child),
                HuckleberryBottleSensor(data["coordinator"], child),
                HuckleberrySolidsSensor(data["coordinator"], child),
                HuckleberryDiaperSensor(data["coordinator"], child),
                HuckleberryPottySensor(data["coordinator"], child),
                HuckleberryGrowthSensor(data["coordinator"], child),
                HuckleberryMedicationSensor(data["coordinator"], child),
                HuckleberryTemperatureSensor(data["coordinator"], child),
                HuckleberryPumpSensor(data["coordinator"], child),
                HuckleberryActivitySensor(data["coordinator"], child),
            )
        )
    async_add_entities(entities)


class HuckleberrySleepSensor(HuckleberryBaseEntity, SensorEntity):
    """Current and previous sleep status."""

    _attr_icon = "mdi:sleep"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = ["active", "paused", "none"]
    _attr_translation_key = "sleep"

    def __init__(
        self,
        coordinator: HuckleberryDataUpdateCoordinator,
        child: HuckleberryChildProfile,
    ) -> None:
        super().__init__(coordinator, child)
        self._attr_unique_id = f"{self.child_uid}_sleep"

    @property
    def native_value(self) -> str | None:
        status = self.coordinator.get_sleep_status(self.child_uid)
        timer = None if status is None else status.timer
        if timer is None:
            return None
        if not timer.active:
            return "none"
        return "paused" if timer.paused else "active"

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        status = self.coordinator.get_sleep_status(self.child_uid)
        if status is None:
            return {}
        result: dict[str, object] = {}
        if status.timer is not None:
            if status.timer.timerStartTime is not None:
                result["current_start"] = as_iso8601_datetime(
                    status.timer.timerStartTime
                )
            if status.timer.timerEndTime is not None and status.timer.paused:
                result["current_end"] = as_iso8601_datetime(status.timer.timerEndTime)
        previous = status.prefs.lastSleep if status.prefs is not None else None
        if previous is not None:
            if previous.start is not None:
                result["previous_start"] = as_iso8601_datetime(previous.start)
            if previous.duration is not None:
                result["previous_duration"] = as_iso8601_duration(previous.duration)
        return result


class HuckleberryNursingSensor(HuckleberryBaseEntity, SensorEntity):
    """Current and previous nursing status."""

    _attr_icon = "mdi:baby-bottle"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = ["active", "paused", "none"]
    _attr_translation_key = "nursing"

    def __init__(
        self,
        coordinator: HuckleberryDataUpdateCoordinator,
        child: HuckleberryChildProfile,
    ) -> None:
        super().__init__(coordinator, child)
        self._attr_unique_id = f"{self.child_uid}_nursing"

    @property
    def native_value(self) -> str | None:
        status = self.coordinator.get_feed_status(self.child_uid)
        timer = None if status is None else status.timer
        if timer is None:
            return None
        if not timer.active:
            return "none"
        return "paused" if timer.paused else "active"

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        status = self.coordinator.get_feed_status(self.child_uid)
        if status is None:
            return {}
        result: dict[str, object] = {}
        timer = status.timer
        if timer is not None and timer.active:
            if timer.feedStartTime is not None:
                result["current_start"] = as_iso8601_datetime(timer.feedStartTime)
            if timer.leftDuration is not None:
                result["current_left_duration"] = as_iso8601_duration(
                    timer.leftDuration
                )
            if timer.rightDuration is not None:
                result["current_right_duration"] = as_iso8601_duration(
                    timer.rightDuration
                )
            if timer.activeSide is not None:
                result["current_active_side"] = timer.activeSide.title()
        previous = status.prefs.lastNursing if status.prefs is not None else None
        if previous is not None:
            if previous.start is not None:
                result["previous_start"] = as_iso8601_datetime(previous.start)
            if previous.duration is not None:
                result["previous_duration"] = as_iso8601_duration(previous.duration)
        return result


class HuckleberryBottleSensor(HuckleberryBaseEntity, SensorEntity):
    """Most recent bottle timestamp."""

    _attr_icon = "mdi:baby-bottle"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_translation_key = "bottle"

    def __init__(
        self,
        coordinator: HuckleberryDataUpdateCoordinator,
        child: HuckleberryChildProfile,
    ) -> None:
        super().__init__(coordinator, child)
        self._attr_unique_id = f"{self.child_uid}_bottle"

    def _latest(self) -> FirebaseLastBottleData | None:
        status = self.coordinator.get_feed_status(self.child_uid)
        return (
            None if status is None or status.prefs is None else status.prefs.lastBottle
        )

    @property
    def native_value(self) -> datetime | None:
        latest = self._latest()
        return as_datetime(None if latest is None else latest.start)

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        latest = self._latest()
        if latest is None:
            return {}
        return {
            key: value
            for key, value in {
                "amount": latest.bottleAmount,
                "units": latest.bottleUnits,
                "type": latest.bottleType,
            }.items()
            if value is not None
        }


class HuckleberrySolidsSensor(HuckleberryBaseEntity, SensorEntity):
    """Most recent solid-food event."""

    _attr_icon = "mdi:food-apple"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_translation_key = "solids"

    def __init__(
        self,
        coordinator: HuckleberryDataUpdateCoordinator,
        child: HuckleberryChildProfile,
    ) -> None:
        super().__init__(coordinator, child)
        self._attr_unique_id = f"{self.child_uid}_solids"

    def _latest(self) -> FirebaseLastSolidData | None:
        status = self.coordinator.get_feed_status(self.child_uid)
        return (
            None if status is None or status.prefs is None else status.prefs.lastSolid
        )

    @property
    def native_value(self) -> datetime | None:
        latest = self._latest()
        return as_datetime(None if latest is None else latest.start)

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        latest = self._latest()
        if latest is None:
            return {}
        foods = (
            []
            if latest.foods is None
            else sorted(food.created_name for food in latest.foods.values())
        )
        reactions = (
            []
            if latest.reactions is None
            else sorted(key for key, value in latest.reactions.items() if value)
        )
        return {
            key: value
            for key, value in {"foods": foods, "reactions": reactions}.items()
            if value
        }


class HuckleberryDiaperSensor(HuckleberryBaseEntity, SensorEntity):
    """Most recent diaper timestamp."""

    _attr_icon = "mdi:baby"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_translation_key = "diaper"

    def __init__(
        self,
        coordinator: HuckleberryDataUpdateCoordinator,
        child: HuckleberryChildProfile,
    ) -> None:
        super().__init__(coordinator, child)
        self._attr_unique_id = f"{self.child_uid}_diaper"

    def _latest(self) -> FirebaseLastDiaperData | None:
        status = self.coordinator.get_diaper_status(self.child_uid)
        return (
            None if status is None or status.prefs is None else status.prefs.lastDiaper
        )

    @property
    def native_value(self) -> datetime | None:
        latest = self._latest()
        return as_datetime(None if latest is None else latest.start)

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        latest = self._latest()
        return (
            {}
            if latest is None or latest.mode is None
            else {"type": latest.mode.title()}
        )


class HuckleberryPottySensor(HuckleberryBaseEntity, SensorEntity):
    """Most recent potty event."""

    _attr_icon = "mdi:toilet"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_translation_key = "potty"

    def __init__(
        self,
        coordinator: HuckleberryDataUpdateCoordinator,
        child: HuckleberryChildProfile,
    ) -> None:
        super().__init__(coordinator, child)
        self._attr_unique_id = f"{self.child_uid}_potty"

    def _latest(self) -> FirebaseLastPottyData | None:
        status = self.coordinator.get_diaper_status(self.child_uid)
        return (
            None if status is None or status.prefs is None else status.prefs.lastPotty
        )

    @property
    def native_value(self) -> datetime | None:
        latest = self._latest()
        return as_datetime(None if latest is None else latest.start)

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        latest = self._latest()
        return (
            {}
            if latest is None or latest.mode is None
            else {"type": latest.mode.title()}
        )


class HuckleberryGrowthSensor(HuckleberryBaseEntity, SensorEntity):
    """Most recent growth measurement timestamp."""

    _attr_icon = "mdi:human-male-height"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_translation_key = "growth"

    def __init__(
        self,
        coordinator: HuckleberryDataUpdateCoordinator,
        child: HuckleberryChildProfile,
    ) -> None:
        super().__init__(coordinator, child)
        self._attr_unique_id = f"{self.child_uid}_growth"

    @property
    def native_value(self) -> datetime | None:
        state = self.coordinator.get_state(self.child_uid)
        growth = None if state is None else state.growth_data
        return as_datetime(None if growth is None else growth.start)

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        state = self.coordinator.get_state(self.child_uid)
        growth = None if state is None else state.growth_data
        if growth is None:
            return {}
        return {
            key: value
            for key, value in {
                "weight": growth.weight,
                "weight_unit": growth.weightUnits,
                "height": growth.height,
                "height_unit": growth.heightUnits,
                "head_circumference": growth.head,
                "head_unit": growth.headUnits,
            }.items()
            if value is not None
        }


class HuckleberryMedicationSensor(HuckleberryBaseEntity, SensorEntity):
    """Most recent medication event."""

    _attr_icon = "mdi:medication"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_translation_key = "medication"

    def __init__(
        self,
        coordinator: HuckleberryDataUpdateCoordinator,
        child: HuckleberryChildProfile,
    ) -> None:
        super().__init__(coordinator, child)
        self._attr_unique_id = f"{self.child_uid}_medication"

    def _latest(self) -> FirebaseMedicationData | None:
        status = self.coordinator.get_health_status(self.child_uid)
        return (
            None
            if status is None or status.prefs is None
            else status.prefs.lastMedication
        )

    @property
    def native_value(self) -> datetime | None:
        latest = self._latest()
        return as_datetime(None if latest is None else latest.start)

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        latest = self._latest()
        if latest is None:
            return {}
        return {
            key: value
            for key, value in {
                "name": latest.medication_name,
                "amount": latest.amount,
                "units": latest.units,
            }.items()
            if value is not None
        }


class HuckleberryTemperatureSensor(HuckleberryBaseEntity, SensorEntity):
    """Most recent recorded temperature."""

    _attr_icon = "mdi:thermometer"
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = None
    _attr_translation_key = "temperature"

    def __init__(
        self,
        coordinator: HuckleberryDataUpdateCoordinator,
        child: HuckleberryChildProfile,
    ) -> None:
        super().__init__(coordinator, child)
        self._attr_unique_id = f"{self.child_uid}_temperature"

    def _latest(self) -> FirebaseTemperatureData | None:
        status = self.coordinator.get_health_status(self.child_uid)
        return (
            None
            if status is None or status.prefs is None
            else status.prefs.lastTemperature
        )

    @property
    def native_value(self) -> int | float | None:
        latest = self._latest()
        return None if latest is None else latest.amount

    @property
    def native_unit_of_measurement(self) -> str | None:
        latest = self._latest()
        if latest is None or latest.units is None:
            return None
        return (
            UnitOfTemperature.CELSIUS
            if latest.units == "C"
            else UnitOfTemperature.FAHRENHEIT
        )

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        latest = self._latest()
        recorded_at = as_iso8601_datetime(None if latest is None else latest.start)
        return {} if recorded_at is None else {"recorded_at": recorded_at}


class HuckleberryPumpSensor(HuckleberryBaseEntity, SensorEntity):
    """Current pumping status with the latest completed event."""

    _attr_icon = "mdi:water-pump"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = ["active", "paused", "none"]
    _attr_translation_key = "pump"

    def __init__(
        self,
        coordinator: HuckleberryDataUpdateCoordinator,
        child: HuckleberryChildProfile,
    ) -> None:
        super().__init__(coordinator, child)
        self._attr_unique_id = f"{self.child_uid}_pump"

    def _latest(self) -> FirebaseLastPumpData | None:
        status = self.coordinator.get_pump_status(self.child_uid)
        return None if status is None or status.prefs is None else status.prefs.lastPump

    @property
    def native_value(self) -> str | None:
        status = self.coordinator.get_pump_status(self.child_uid)
        timer = None if status is None else status.timer
        if timer is None or not timer.active:
            return "none" if status is not None else None
        return "paused" if timer.paused else "active"

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        status = self.coordinator.get_pump_status(self.child_uid)
        timer = None if status is None else status.timer
        latest = self._latest()
        values: dict[str, object | None] = {
            "current_start": as_iso8601_datetime(
                None if timer is None else timer.startTime
            ),
            "current_mode": None if timer is None else timer.entryMode,
            "previous_start": as_iso8601_datetime(
                None if latest is None else latest.start
            ),
            "previous_duration": as_iso8601_duration(
                None if latest is None else latest.duration
            ),
            "previous_left_amount": None if latest is None else latest.leftAmount,
            "previous_right_amount": None if latest is None else latest.rightAmount,
            "units": None if latest is None else latest.units,
        }
        return {key: value for key, value in values.items() if value is not None}


class HuckleberryActivitySensor(HuckleberryBaseEntity, SensorEntity):
    """Most recent or currently active care activity."""

    _attr_icon = "mdi:human-child"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = [
        "bath",
        "brush_teeth",
        "indoor_play",
        "outdoor_play",
        "screen_time",
        "skin_to_skin",
        "story_time",
        "tummy_time",
        "none",
    ]
    _attr_translation_key = "activity"

    _MODES = {
        "bath": "bath",
        "brushTeeth": "brush_teeth",
        "indoorPlay": "indoor_play",
        "outdoorPlay": "outdoor_play",
        "screenTime": "screen_time",
        "skinToSkin": "skin_to_skin",
        "storyTime": "story_time",
        "tummyTime": "tummy_time",
    }

    def __init__(
        self,
        coordinator: HuckleberryDataUpdateCoordinator,
        child: HuckleberryChildProfile,
    ) -> None:
        super().__init__(coordinator, child)
        self._attr_unique_id = f"{self.child_uid}_activity"

    def _candidates(self) -> dict[str, FirebaseLastActivityData | None]:
        status = self.coordinator.get_activity_status(self.child_uid)
        prefs = None if status is None else status.prefs
        if prefs is None:
            return {}
        return {
            "bath": prefs.lastBath,
            "brushTeeth": prefs.lastBrushTeeth,
            "indoorPlay": prefs.lastIndoorPlay,
            "outdoorPlay": prefs.lastOutdoorPlay,
            "screenTime": prefs.lastScreenTime,
            "skinToSkin": prefs.lastSkinToSkin,
            "storyTime": prefs.lastStoryTime,
            "tummyTime": prefs.lastTummyTime,
        }

    def _latest(self) -> tuple[str, FirebaseLastActivityData] | None:
        candidates = [
            (mode, event)
            for mode, event in self._candidates().items()
            if event is not None and event.start is not None
        ]
        return (
            max(candidates, key=lambda item: float(item[1].start))
            if candidates
            else None
        )

    @property
    def native_value(self) -> str | None:
        status = self.coordinator.get_activity_status(self.child_uid)
        timer = None if status is None else status.timer
        if timer is not None:
            active = {
                "bath": timer.bath,
                "brushTeeth": timer.brushTeeth,
                "indoorPlay": timer.indoorPlay,
                "outdoorPlay": timer.outdoorPlay,
                "screenTime": timer.screenTime,
                "skinToSkin": timer.skinToSkin,
                "storyTime": timer.storyTime,
                "tummyTime": timer.tummyTime,
            }
            for mode, event in active.items():
                if event is not None and event.active:
                    return self._MODES[mode]
        latest = self._latest()
        if latest is not None:
            return self._MODES[latest[0]]
        return "none" if status is not None else None

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        latest = self._latest()
        if latest is None:
            return {}
        _, event = latest
        return {
            key: value
            for key, value in {
                "previous_start": as_iso8601_datetime(event.start),
                "previous_duration": as_iso8601_duration(event.duration),
            }.items()
            if value is not None
        }
