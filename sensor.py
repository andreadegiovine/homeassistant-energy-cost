import logging

from homeassistant.core import HomeAssistant
from homeassistant.const import CURRENCY_EURO, UnitOfEnergy
from homeassistant.config_entries import ConfigEntry
from homeassistant.components.sensor import SensorEntityDescription

from .base import EnergyCostBase
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


class KwhCost(EnergyCostBase):
    @property
    def state(self):
        self._attr_extra_state_attributes = {
            "net_cost": self._coordinator.get_current_kwh_rate,
            "vat_included_cost": self._coordinator.get_vat_included_amount(self._coordinator.get_kwh_cost())
        }
        return self._coordinator.get_kwh_cost()

class MonthlyTotalCost(EnergyCostBase):
    @property
    def state(self):
        monthly_energy = 0
        if "energy" in self._attr_extra_state_attributes:
            monthly_energy = self._attr_extra_state_attributes["energy"]

        new_energy = self._coordinator.get_power_entity_state
        if monthly_energy > 0:
            new_energy = new_energy - monthly_energy

        total_energy = monthly_energy + new_energy
        total_energy_cost = self._coordinator.get_kwh_cost(total_energy)

        monthly_cost = 0
        if "last_energy_cost" in self._data and self._data["last_energy_cost"] > 0:
            monthly_cost = self._data["last_energy_cost"]

        new_cost = self._coordinator.get_kwh_cost(new_energy)

        total_cost = monthly_cost + new_cost

        grand_total = self._coordinator.get_vat_included_amount(total_cost + self._coordinator.get_monthly_fee)

        self._attr_extra_state_attributes = {
            "energy": total_energy,
            "energy_cost": total_energy_cost,
            "fixed_cost": self._coordinator.get_monthly_fee,
            "vat_cost": (total_energy_cost + self._coordinator.get_monthly_fee) * self._coordinator.config_vat_fee,
            "total_kwh_cost": grand_total / total_energy
        }

        self._data["last_energy_cost"] = total_energy_cost
        return grand_total