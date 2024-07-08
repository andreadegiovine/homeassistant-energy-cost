import logging

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from .base import EnergyCostCoordinator
from .const import (
                       DOMAIN,
                       PLATFORMS,
                       FIELD_POWER,
                       FIELD_PUN_MODE,
                       FIELD_RATE_MODE,
                       FIELD_RATE_MODE_MONO,
                       FIELD_RATE_MODE_FLEX,
                       FIELD_MONO_RATE,
                       FIELD_F1_RATE,
                       FIELD_F2_RATE,
                       FIELD_F3_RATE,
                       FIELD_FIXED_FEE,
                       FIELD_POWER_ENTITY,
                       FIELD_PUN_ENTITY,
                       FIELD_CURRENT_RATE_ENTITY
                   )

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, config: ConfigEntry):

    coordinator = EnergyCostCoordinator(hass, config)
    hass.data.setdefault(DOMAIN, {})[config.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(config, PLATFORMS)

    # Return boolean to indicate that initialization was successful.
    return True
