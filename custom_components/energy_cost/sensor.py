import logging

from homeassistant.core import HomeAssistant
from homeassistant.const import CURRENCY_EURO, UnitOfEnergy
from homeassistant.config_entries import ConfigEntry
from homeassistant.components.sensor import SensorEntityDescription

from .base import EnergyCostSensor
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
                       FIELD_POWER_ENTITY,
                       FIELD_PUN_ENTITY,
                       FIELD_CURRENT_RATE_ENTITY
                   )

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, config: ConfigEntry, async_add_entities):
    coordinator = hass.data[DOMAIN][config.entry_id]

    sensors = []

    description = SensorEntityDescription(
        key='kwh_cost',
        name='kwh_cost',
        translation_key = 'kwh_cost',
        native_unit_of_measurement = f"{CURRENCY_EURO}/{UnitOfEnergy.KILO_WATT_HOUR}"
    )
    sensors.extend([KwhCost(coordinator, description)])

    description = SensorEntityDescription(
        key='monthly_total_cost',
        name='monthly_total_cost',
        translation_key = 'monthly_total_cost',
        native_unit_of_measurement = CURRENCY_EURO
    )
    sensors.extend([MonthlyTotalCost(coordinator, description)])

    async_add_entities(sensors)


class KwhCost(EnergyCostSensor):
    def update_sensor(self):
        self._attr_extra_state_attributes = {
            "net_cost": self._coordinator.get_current_kwh_rate,
            "real_cost": self._coordinator.get_kwh_cost(),
            "vat_cost": self._coordinator.get_kwh_cost() * self._coordinator.config_vat_fee
        }
        self._attr_native_value = self._coordinator.get_vat_included_amount(self._coordinator.get_kwh_cost())

class MonthlyTotalCost(EnergyCostSensor):
    def update_sensor(self):

        current_energy = 0
        if "energy" in self._attr_extra_state_attributes:
            current_energy = self._attr_extra_state_attributes["energy"]

        current_energy_cost = 0
        if "energy_cost" in self._attr_extra_state_attributes:
            current_energy_cost = self._attr_extra_state_attributes["energy_cost"]

        new_energy = self._coordinator.get_power_entity_state - current_energy
        new_energy_cost = self._coordinator.get_kwh_cost(new_energy)

        total_energy = current_energy + new_energy
        total_energy_cost = current_energy_cost + new_energy_cost

        vat_cost = (total_energy_cost + self._coordinator.get_monthly_fee) * self._coordinator.config_vat_fee

        total_cost = self._coordinator.get_vat_included_amount(total_energy_cost + self._coordinator.get_monthly_fee)

        kwh_cost = 0
        if total_cost > 0 and total_energy > 0:
            kwh_cost = total_cost / total_energy

        self._attr_extra_state_attributes = {
            "energy": total_energy,
            "energy_cost": total_energy_cost,
            "fixed_cost": self._coordinator.get_monthly_fee,
            "vat_cost": vat_cost,
            "total_kwh_cost": kwh_cost
        }

        self._attr_native_value = total_cost