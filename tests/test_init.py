"""Test Huckleberry component setup."""

from unittest.mock import patch
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from custom_components.huckleberry.const import DOMAIN
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry


async def test_setup_entry(hass: HomeAssistant, mock_huckleberry_api):
    """Test setting up the integration."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_EMAIL: "test@example.com",
            CONF_PASSWORD: "test_password",
        },
    )
    entry.add_to_hass(hass)

    with patch(
        "custom_components.huckleberry.HuckleberryReadOnlyAPI",
        return_value=mock_huckleberry_api,
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert entry.state.value == "loaded"
    expected_entities = {
        "sensor.test_child_sleep",
        "sensor.test_child_nursing",
        "sensor.test_child_bottle",
        "sensor.test_child_solids",
        "sensor.test_child_diaper",
        "sensor.test_child_potty",
        "sensor.test_child_growth",
        "sensor.test_child_medication",
        "sensor.test_child_temperature",
        "sensor.test_child_pumping",
        "sensor.test_child_activity",
        "calendar.test_child_care_history",
    }
    assert expected_entities <= {state.entity_id for state in hass.states.async_all()}
    assert hass.services.async_services().get(DOMAIN) is None
    assert all(not entity_id.startswith("switch.") for entity_id in expected_entities)

    for listener_name in (
        "setup_sleep_listener",
        "setup_feed_listener",
        "setup_health_listener",
        "setup_diaper_listener",
        "setup_child_listener",
        "setup_pump_listener",
        "setup_activity_listener",
    ):
        getattr(mock_huckleberry_api, listener_name).assert_awaited_once()
