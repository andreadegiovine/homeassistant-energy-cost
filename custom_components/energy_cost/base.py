
import logging
from datetime import datetime
from dateutil.relativedelta import relativedelta

from homeassistant.core import callback
from homeassistant.helpers.update_coordinator import ( CoordinatorEntity, DataUpdateCoordinator )
from homeassistant.helpers.event import ( async_track_state_change, async_track_point_in_time )
from homeassistant.components.sensor import ( SensorEntity, SensorStateClass, SensorDeviceClass )

from .const import (
                       DOMAIN,
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

class EnergyCostCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, config):
        super().__init__(hass, _LOGGER, name = DOMAIN)

        self._hass = hass

        self.config = config.data
        self.config_power_entity = self.config[FIELD_POWER_ENTITY]
        self.config_power = float(self.config[FIELD_POWER])
        self.config_rate_mode = self.config[FIELD_RATE_MODE]
        self.config_pun_mode = self.config[FIELD_PUN_MODE]
        self.config_fixed_fee = float(self.config[FIELD_FIXED_FEE])
        self.config_vat_fee = float(self.config[FIELD_VAT_FEE]) / 100

        if FIELD_PUN_ENTITY in self.config:
            self.config_pun_entity = self.config[FIELD_PUN_ENTITY]

        if FIELD_MONO_RATE in self.config:
            self.config_mono_rate = float(self.config[FIELD_MONO_RATE])
        else:
            self.config_current_rate_entity = self.config[FIELD_CURRENT_RATE_ENTITY]
            self.config_f1_rate = float(self.config[FIELD_F1_RATE])
            self.config_f2_rate = float(self.config[FIELD_F2_RATE])
            self.config_f3_rate = float(self.config[FIELD_F3_RATE])

    @property
    def get_power_entity_state(self):
        entity_obj =  self._hass.states.get(self.config_power_entity)

        if not entity_obj or entity_obj.state == 'unknown':
            return 0

        state = entity_obj.state
        return float(state)

    @property
    def get_current_rate_entity_state(self):
        entity_obj =  self._hass.states.get(self.config_current_rate_entity)

        if not entity_obj or entity_obj.state == 'unknown':
            return None

        state = entity_obj.state
        return state.lower()

    @property
    def get_pun_entity_state(self):
        entity_obj =  self._hass.states.get(self.config_pun_entity)

        if not entity_obj or entity_obj.state == 'unknown':
            return 0

        state = entity_obj.state
        return float(state)

    @property
    def get_current_kwh_rate(self):
        rate = 0

        if self.config_rate_mode == FIELD_RATE_MODE_MONO:
            rate = self.config_mono_rate
        elif self.get_current_rate_entity_state:
            rate = float(self.config[f"{self.get_current_rate_entity_state}_rate"])

        if self.config_pun_mode:
            rate = rate + self.get_pun_entity_state

        return rate

    @property
    def get_monthly_fee(self):
        # Commercializzazione
        monthly_fee = self.config_fixed_fee
        # Quota fissa
        monthly_fee = monthly_fee + 1.84
        # Quota potenza
        monthly_fee = monthly_fee + (1.85 * self.config_power)
        # Quota continuità
        monthly_fee = monthly_fee + (0.016567 * self.config_power)

        return monthly_fee

    def get_kwh_cost(self, qty = 1):
        consumption_fee = 0
        # Capacità
        consumption_fee = consumption_fee + ((qty + (qty * 0.1)) * 0.003486)
        # Dispacciamento
        consumption_fee = consumption_fee + ((qty + (qty * 0.1)) * 0.006980)
        # Quota energia
        consumption_fee = consumption_fee + (qty * 0.010570)
        # Squilibri
        consumption_fee = consumption_fee + (qty * 0.00156)
        # Continuità
        consumption_fee = consumption_fee + (qty * 0.00007)
        # Arim
        consumption_fee = consumption_fee + (qty * 0.006987)
        # Asos
        consumption_fee = consumption_fee + (qty * 0.025398)
        # Imposte
        consumption_fee = consumption_fee + (qty * 0.0227)
        # Fornitura
        consumption_fee = consumption_fee + (qty * self.get_current_kwh_rate)

        return consumption_fee

    def get_vat_included_amount(self, amount):
        return amount + (amount * self.config_vat_fee)


class EnergyCostBase(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator: EnergyCostCoordinator, description):
        super().__init__(coordinator)

        self._coordinator = coordinator
        self._data = {}
        self.scheduled = None

        self.entity_description = description
        self._attr_unique_id = "energy_cost_" + description.key
        self._available = True
#         self._attr_name = "energy_cost_" + description.key
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_device_class = SensorDeviceClass.MONETARY
        self._attr_extra_state_attributes = {}
        self._attr_suggested_display_precision = 2
        self._attr_translation_key = description.translation_key
        self._attr_has_entity_name = True

        self.schedule_monthly_reset()

        async_track_state_change(self._coordinator.hass, self._coordinator.config_power_entity, self._async_on_change)

        if FIELD_CURRENT_RATE_ENTITY in self._coordinator.config:
            async_track_state_change(self._coordinator.hass, self._coordinator.config_current_rate_entity, self._async_on_change)


    def schedule_monthly_reset(self):
        next_run = datetime.now().replace(day=1, hour=00, minute=00, second=00, microsecond=000000) + relativedelta(months=+1)
        _LOGGER.error(next_run)

        if self.scheduled is not None:
            self._attr_extra_state_attributes = {}
            self._data = {}
            self._attr_state = 0

            self.scheduled()
            self.scheduled = None

        self.scheduled = async_track_point_in_time(self._coordinator.hass, self.schedule_monthly_reset, next_run)

    @callback
    def _async_on_change(self, _, old_state, new_state):
        self.async_write_ha_state()