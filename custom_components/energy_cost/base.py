
import logging
from datetime import ( datetime, UTC )
from dateutil.relativedelta import relativedelta

from homeassistant.core import callback
from homeassistant.helpers.update_coordinator import ( CoordinatorEntity, DataUpdateCoordinator )
from homeassistant.helpers.event import ( async_track_state_change, async_track_point_in_time )
from homeassistant.components.sensor import ( RestoreSensor, SensorStateClass, SensorDeviceClass )
from homeassistant.components.number import NumberEntity
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.util import dt

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
                       FIELD_CURRENT_RATE_ENTITY,
                       DISPBT,
                       TRASPORTO_QUOTA_FISSA,
                       TRASPORTO_QUOTA_POTENZA,
                       UC6_CONTINUITA_FISSO,
                       UC6_CONTINUITA,
                       CORRISPETTIVO_CAPACITA,
                       DISPACCIAMENTO,
                       TRASPORTO_QUOTA_ENERGIA,
                       UC3_COPERTURA_SQUILIBRI,
                       ARIM,
                       ASOS,
                       IMPOSTA_ERARIALE
                   )
_LOGGER = logging.getLogger(__name__)

class EnergyCostCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, config):
        super().__init__(hass, _LOGGER, name = DOMAIN)

        self._hass = hass

        self.unique_id = config.unique_id
        self.config = config.data
        self.config_power_entity = self.config[FIELD_POWER_ENTITY]
        self.config_power = float(self.config[FIELD_POWER])
        self.config_rate_mode = self.config[FIELD_RATE_MODE]
        self.config_pun_mode = self.config[FIELD_PUN_MODE]
        self.config_fixed_fee = float(self.config[FIELD_FIXED_FEE])
        self.config_vat_fee = float(self.config[FIELD_VAT_FEE]) / 100
        self.extra_monthly_power = 0

        self.device_name = "Energy cost"
        if FIELD_NAME in self.config:
            self.device_name = self.config[FIELD_NAME]

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

        if not entity_obj or entity_obj.state in ('unknown','unavailable'):
            return float(self.extra_monthly_power)

        state = entity_obj.state
        return float(state) + float(self.extra_monthly_power)

    @property
    def get_current_rate_entity_state(self):
        entity_obj =  self._hass.states.get(self.config_current_rate_entity)

        if not entity_obj or entity_obj.state in ('unknown','unavailable'):
            return None

        state = entity_obj.state
        return state.lower()

    @property
    def get_pun_entity_state(self):
        entity_obj =  self._hass.states.get(self.config_pun_entity)

        if not entity_obj or entity_obj.state in ('unknown','unavailable'):
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
        monthly_fee = monthly_fee + TRASPORTO_QUOTA_FISSA
        # DISPbt
        monthly_fee = monthly_fee + DISPBT
        # Quota potenza
        monthly_fee = monthly_fee + (TRASPORTO_QUOTA_POTENZA * self.config_power)
        # Quota continuità
        monthly_fee = monthly_fee + (UC6_CONTINUITA_FISSO * self.config_power)

        return monthly_fee

    def get_kwh_cost(self, qty = 1):
        consumption_fee = 0
        # Capacità
        consumption_fee = consumption_fee + ((qty + (qty * 0.1)) * CORRISPETTIVO_CAPACITA)
        # Dispacciamento
        consumption_fee = consumption_fee + ((qty + (qty * 0.1)) * DISPACCIAMENTO)
        # Quota energia
        consumption_fee = consumption_fee + (qty * TRASPORTO_QUOTA_ENERGIA)
        # Squilibri
        consumption_fee = consumption_fee + (qty * UC3_COPERTURA_SQUILIBRI)
        # Continuità
        consumption_fee = consumption_fee + (qty * UC6_CONTINUITA)
        # Arim
        consumption_fee = consumption_fee + (qty * ARIM)
        # Asos
        consumption_fee = consumption_fee + (qty * ASOS)
        # Fornitura
        consumption_fee = consumption_fee + (qty * self.get_current_kwh_rate)

        # Imposte
        if self.config_power > 3 or qty > 150:
            consumption_fee = consumption_fee + (qty * IMPOSTA_ERARIALE)

        return consumption_fee

    def get_vat_included_amount(self, amount):
        return amount + (amount * self.config_vat_fee)


class EnergyCostBase(CoordinatorEntity):
    def __init__(self, coordinator: EnergyCostCoordinator, description):
        super().__init__(coordinator)
        # Component
        self._coordinator = coordinator
        self.is_loaded = None
        self.is_scheduled = None
        self.is_reset = None
        self.restored_data = None
        self.is_restored = None
        # Core
        self.entity_description = description
        self._attr_unique_id = "energy_cost_" + self._coordinator.unique_id + "_" + description.key
        self._attr_native_value = 0
        self._available = True
        self._attr_state_class = SensorStateClass.TOTAL
        self._attr_device_class = SensorDeviceClass.MONETARY
        self._attr_extra_state_attributes = {}
        self._attr_suggested_display_precision = 2
        self._attr_translation_key = description.translation_key
        self._attr_has_entity_name = True

    @property
    def device_info(self):
        return {
            "identifiers": {
                (DOMAIN, self._coordinator.device_name, "Energy cost")
            },
            "name": self._coordinator.device_name,
            "model": self._coordinator.device_name,
            "manufacturer": "Energy cost"
        }


class EnergyCostSensor(EnergyCostBase, RestoreSensor):
    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        # Restore data
        self.restored_data = await self.async_get_last_state()
        if self.restored_data:
            self.is_restored = True
        # Monthly reset
        await self._scheduled_monthly_reset()
        # Update on price/energy change
        async_track_state_change(self._coordinator.hass, self._coordinator.config_power_entity, self._async_on_change)
        if FIELD_CURRENT_RATE_ENTITY in self._coordinator.config:
            async_track_state_change(self._coordinator.hass, self._coordinator.config_current_rate_entity, self._async_on_change)

    def restore_data(self):
        self.is_restored = None
        self._attr_native_value = self.restored_data.state
        for key in self.restored_data.attributes:
            if isinstance(self.restored_data.attributes[key], (int, float)):
                self._attr_extra_state_attributes[key] = self.restored_data.attributes[key]

    def reset_data(self):
        self.is_reset = None
        self._attr_native_value = 0
        for key in self._attr_extra_state_attributes:
            if isinstance(self._attr_extra_state_attributes[key], (int, float)):
                self._attr_extra_state_attributes[key] = 0
        if float(self._coordinator.extra_monthly_power) > 0:
            self._coordinator.extra_monthly_power = 0

    def prevent_update(self):
        if self.is_reset:
            self.reset_data()
            return True
        if self.is_restored:
            self.restore_data()
            return True
        return False

    async def _scheduled_monthly_reset(self, now=None):

        def get_datetime():
            date = datetime.now()
            if date.tzinfo != UTC:
                date = date.astimezone(UTC)
            return date.astimezone(dt.get_default_time_zone())

        next_run = get_datetime().replace(day=1, hour=00, minute=00, second=00, microsecond=000000) + relativedelta(months=+1)

        if self.is_scheduled is not None:
            self.is_scheduled()
            self.is_scheduled = None
            self.is_reset = True
            await self._update_sensor()

        self.is_scheduled = async_track_point_in_time(self._coordinator.hass, self._scheduled_monthly_reset, next_run)

    async def _async_on_change(self, _, old_state, new_state):
        if new_state.state != "unknown":
            self.is_loaded = True

        if self.is_loaded:
            await self._update_sensor()

    @callback
    def _handle_coordinator_update(self):
        self.update_sensor()
        self.async_write_ha_state()

    async def _update_sensor(self):
        if not self.prevent_update():
            self.update_sensor()
        self.async_write_ha_state()

    def update_sensor(self):
        raise NotImplementedError


class EnergyCostNumber(EnergyCostBase, NumberEntity, RestoreEntity):
    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        restored_data = await self.async_get_last_state()
        value = 0
        if restored_data and restored_data.state not in ["unavailable", "unknown"]:
            value = restored_data.state
        self._attr_native_value = value
        self._coordinator.extra_monthly_power = float(value)

    @property
    def native_value(self):
        return self._coordinator.extra_monthly_power

    async def async_set_native_value(self, value: float) -> None:
        self._attr_native_value = value
        self._coordinator.extra_monthly_power = value
        self._coordinator.async_update_listeners()