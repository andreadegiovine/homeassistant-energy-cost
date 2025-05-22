from homeassistant import config_entries
import voluptuous as vol
from homeassistant.helpers.selector import selector
import logging
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

def DATA_SCHEMA_1(reconfig=None):
    defaults = {
        FIELD_NAME: "Home",
        FIELD_POWER_ENTITY: None,
        FIELD_POWER: 4.5,
        FIELD_RATE_MODE: FIELD_RATE_MODE_FLEX,
        FIELD_PUN_MODE: True
    }

    step_schema = vol.Schema({})
    if reconfig:
        defaults = reconfig
    else:
        step_schema = step_schema.extend({vol.Required(FIELD_NAME, default=defaults[FIELD_NAME]): str})

    return step_schema.extend({
        vol.Required(FIELD_POWER_ENTITY, default=defaults[FIELD_POWER_ENTITY]): selector({"entity": {"device_class": "energy"}}),
        vol.Required(FIELD_POWER, default=defaults[FIELD_POWER]): vol.Coerce(float),
        vol.Required(FIELD_RATE_MODE, default=defaults[FIELD_RATE_MODE]): selector({"select": {
            "options": [FIELD_RATE_MODE_MONO, FIELD_RATE_MODE_FLEX], "mode": "dropdown",
            "translation_key": FIELD_RATE_MODE}}),
        vol.Required(FIELD_PUN_MODE, default=defaults[FIELD_PUN_MODE]): selector({"boolean": {}})
    })

def DATA_SCHEMA_2(reconfig=None):
    defaults = {
        FIELD_FIXED_FEE: 6.50,
        FIELD_VAT_FEE: 10
    }
    if reconfig:
        defaults = reconfig
    return vol.Schema({
        vol.Optional(FIELD_FIXED_FEE, default=defaults[FIELD_FIXED_FEE]): vol.Coerce(float),
        vol.Required(FIELD_VAT_FEE, default=defaults[FIELD_VAT_FEE]): vol.Coerce(float),
    })

def DATA_SCHEMA_3(reconfig=None):
    defaults = {
        FIELD_PUN_ENTITY: None
    }
    if reconfig:
        defaults = reconfig
    return {
        vol.Required(FIELD_PUN_ENTITY, default=defaults[FIELD_PUN_ENTITY]): selector({ "entity": { "integration": "pun_sensor", "domain": "sensor" } })
    }

def DATA_SCHEMA_4(reconfig=None):
    defaults = {
        FIELD_MONO_RATE: 0.01328
    }
    if reconfig:
        defaults = reconfig
    return {
        vol.Required(FIELD_MONO_RATE, default=defaults[FIELD_MONO_RATE]): vol.Coerce(float)
    }

def DATA_SCHEMA_5(reconfig=None):
    defaults = {
        FIELD_CURRENT_RATE_ENTITY: None,
        FIELD_F1_RATE: 0.01328,
        FIELD_F2_RATE: 0.01328,
        FIELD_F3_RATE: 0.01328,
    }
    if reconfig:
        defaults = reconfig
    return {
        vol.Required(FIELD_CURRENT_RATE_ENTITY, default=defaults[FIELD_CURRENT_RATE_ENTITY]): selector({ "entity": { "device_class": "enum", "integration": "pun_sensor", "domain": "sensor" } }),
        vol.Required(FIELD_F1_RATE, default=defaults[FIELD_F1_RATE]): vol.Coerce(float),
        vol.Required(FIELD_F2_RATE, default=defaults[FIELD_F2_RATE]): vol.Coerce(float),
        vol.Required(FIELD_F3_RATE, default=defaults[FIELD_F3_RATE]): vol.Coerce(float),
    }


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Example config flow."""
    # The schema version of the entries that it creates
    # Home Assistant will call your migrate method if the version changes
    VERSION = 1
    MINOR_VERSION = 1

    def __init__(self):
        """Initialize config flow."""
        self.data = None
        self.reconfig = None

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""

        if user_input is not None:
            self.data = user_input

            if self.source == config_entries.SOURCE_RECONFIGURE:
                unique_id = self.reconfig[FIELD_NAME].lower()
            else:
                unique_id = self.data[FIELD_NAME].lower()

            await self.async_set_unique_id(unique_id)

            if self.source != config_entries.SOURCE_RECONFIGURE:
                self._abort_if_unique_id_configured()

            return await self.async_step_final()

        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA_1(self.reconfig)
        )

    async def async_step_final(self, user_input=None):
        """Handle the final step."""

        step_schema = DATA_SCHEMA_2(self.reconfig)

        if user_input is not None:
            if user_input[FIELD_FIXED_FEE] is not None:
                config_data = dict()
                config_data.update(self.data)
                config_data.update(user_input)
                _LOGGER.info(config_data)
                if self.source == config_entries.SOURCE_RECONFIGURE:
                    return self.async_update_reload_and_abort(self._get_reconfigure_entry(),  data_updates=config_data)
                return self.async_create_entry(title=config_data[FIELD_NAME], data=config_data)

        if self.data[FIELD_PUN_MODE]:
            step_schema = step_schema.extend(DATA_SCHEMA_3(self.reconfig))

        if self.data[FIELD_RATE_MODE] == FIELD_RATE_MODE_MONO:
            step_schema = step_schema.extend(DATA_SCHEMA_4(self.reconfig))
        else:
            step_schema = step_schema.extend(DATA_SCHEMA_5(self.reconfig))

        return self.async_show_form(
            step_id="final", data_schema=step_schema
        )

    async def async_step_reconfigure(self, user_input):
        self.reconfig = self._get_reconfigure_entry().data
        _LOGGER.info(self.reconfig)
        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA_1(self.reconfig)
        )