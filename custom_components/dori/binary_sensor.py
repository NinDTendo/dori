"""Sensor platform for Dori - Day of Rest Indicator integration."""
from __future__ import annotations

from datetime import datetime, timedelta
import logging

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Initialize Dori - Day of Rest Indicator config entry."""
    registry = er.async_get(hass)
    calendars = [
        er.async_validate_entity_id(registry, item)
        for item in config_entry.options.get("calendar_entities", [])
    ]
    name = config_entry.title
    unique_id = config_entry.entry_id

    async_add_entities([doriBinarySensorEntity(hass, unique_id, name, calendars)])


class doriBinarySensorEntity(BinarySensorEntity):
    """dori Sensor."""

    def __init__(
        self, hass: HomeAssistant, unique_id: str, name: str, wrapped_entity_id: str
    ) -> None:
        """Initialize dori Sensor."""
        super().__init__()
        self.hass = hass
        self._state = False
        self._wrapped_entity_id = wrapped_entity_id
        self._attr_name = name
        self._attr_unique_id = unique_id
        self._listeners = []

    @property
    def is_on(self) -> bool:
        """Return True if the binary sensor is on."""
        return self._state

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return {"calendars": self._wrapped_entity_id}

    async def async_added_to_hass(self) -> None:
        """Connect listeners when added to hass."""
        _LOGGER.debug("Adding listeners for %s", self._wrapped_entity_id)
        self._listeners.append(
            async_track_state_change_event(
                self.hass, self._wrapped_entity_id, self.update
            )
        )
        self.update()

    def get_next_day(self) -> datetime.date:
        """Return the date of the next day."""
        r = (datetime.now() + timedelta(hours=12)).date()
        _LOGGER.info("Next day: %s", r)
        return r

    def get_next_event_start(self, entity_id: str) -> datetime.date | None:
        """Return the date of the next event."""
        start_time = self.hass.states.get(entity_id).attributes.get("start_time")

        if start_time is not None:
            return datetime.strptime(
                start_time,
                "%Y-%m-%d %H:%M:%S",
            ).date()
        else:
            return None

    def day_off(self, day: datetime, next_events: list[str]) -> bool:
        """Return True if today is a day off."""
        _LOGGER.debug("day: %s", day)
        _LOGGER.debug("next_events: %s", next_events)
        _LOGGER.debug("day in next_events: %s", day in next_events)
        return day not in next_events

    def update(self, *args) -> None:
        """Update the sensor."""
        # _LOGGER.info("Updating sensor")
        next_events = [
            self.get_next_event_start(entity_id)
            for entity_id in self._wrapped_entity_id
        ]
        self._state = self.day_off(self.get_next_day(), next_events)
        _LOGGER.debug("self._state: %s", self._state)

    async def async_will_remove_from_hass(self) -> None:
        """Disconnect listeners on removal."""
        for listener in self._listeners:
            listener()
        self._listeners.clear()
