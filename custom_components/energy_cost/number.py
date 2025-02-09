import logging

from homeassistant.core import HomeAssistant
from homeassistant.const import UnitOfEnergy
from homeassistant.config_entries import ConfigEntry
from homeassistant.components.number import NumberEntityDescription
from homeassistant.components.number.const import NumberMode

from .base import EnergyCostNumber
from .const import (
                       DOMAIN
                   )

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, config: ConfigEntry, async_add_entities):
    coordinator = hass.data[DOMAIN][config.entry_id]

    sensors = []

    description = NumberEntityDescription(
        key='extra_monthly_energy',
        name='extra_monthly_energy',
        translation_key = 'extra_monthly_energy',
        native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR,
        native_min_value = 0,
        native_max_value = 999999999,
        native_step = 1,
        mode = NumberMode.BOX
    )
    sensors.extend([EnergyCostNumber(coordinator, description)])

    async_add_entities(sensors)