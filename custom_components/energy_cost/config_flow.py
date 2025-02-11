from homeassistant import config_entries
import voluptuous as vol
from homeassistant.helpers.selector import selector
import logging
import string
import random
from .const import (
                        DOMAIN,
                        FIELD_NAME,
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
                        FIELD_VAT_FEE,
                        FIELD_POWER_ENTITY,
                        FIELD_PUN_ENTITY,
                        FIELD_CURRENT_RATE_ENTITY
                    )

_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA_1 = vol.Schema({
    vol.Required(FIELD_NAME, default="Home"): str,
    vol.Required(FIELD_POWER_ENTITY): selector({ "entity": { "device_class": "energy" } }),
    vol.Required(FIELD_POWER, default=4.5): vol.Coerce(float),
    vol.Required(FIELD_RATE_MODE, default=FIELD_RATE_MODE_FLEX): selector({ "select": { "options": [FIELD_RATE_MODE_MONO, FIELD_RATE_MODE_FLEX], "mode": "dropdown", "translation_key": FIELD_RATE_MODE } }),
    vol.Required(FIELD_PUN_MODE, default=True): selector({ "boolean": {} })
})

DATA_SCHEMA_2 = vol.Schema({
    vol.Optional(FIELD_FIXED_FEE, default=6.50): vol.Coerce(float),
    vol.Required(FIELD_VAT_FEE, default=10): vol.Coerce(float),
})


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Example config flow."""
    # The schema version of the entries that it creates
    # Home Assistant will call your migrate method if the version changes
    VERSION = 1
    MINOR_VERSION = 1

    def __init__(self):
        """Initialize config flow."""
        self.data = None

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""

        if user_input is not None:
            self.data = user_input
            unique_id = res = ''.join(random.choices(string.ascii_letters, k=10))
            await self.async_set_unique_id(unique_id)
            return await self.async_step_final()

        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA_1
        )

    async def async_step_final(self, user_input=None):
        """Handle the final step."""

        step_schema = DATA_SCHEMA_2

        if user_input is not None:
            if user_input[FIELD_FIXED_FEE] is not None:
                config_data = dict()
                config_data.update(self.data)
                config_data.update(user_input)
                _LOGGER.info(config_data)
                return self.async_create_entry(title=config_data[FIELD_NAME], data=config_data)

        if self.data[FIELD_PUN_MODE]:
            step_schema = step_schema.extend({
                vol.Required(FIELD_PUN_ENTITY): selector({ "entity": { "integration": "pun_sensor", "domain": "sensor" } })
            })

        if self.data[FIELD_RATE_MODE] == FIELD_RATE_MODE_MONO:
            step_schema = step_schema.extend({
                vol.Required(FIELD_MONO_RATE, default=0.01328): vol.Coerce(float)
            })
        else:
            step_schema = step_schema.extend({
                vol.Required(FIELD_CURRENT_RATE_ENTITY): selector({ "entity": { "device_class": "enum", "integration": "pun_sensor", "domain": "sensor" } }),
                vol.Required(FIELD_F1_RATE, default=0.01328): vol.Coerce(float),
                vol.Required(FIELD_F2_RATE, default=0.01328): vol.Coerce(float),
                vol.Required(FIELD_F3_RATE, default=0.01328): vol.Coerce(float),
            })

        return self.async_show_form(
            step_id="final", data_schema=step_schema
        )
