"""Basic radiator control through external temperature sensor."""
import datetime
import typing

import appdaemon.plugins.hass.hassapi
import appdaemon.entity

PERIOD_MINUTES = 15


class RadiatorApp(appdaemon.plugins.hass.hassapi.Hass):
    entity_radiator: appdaemon.entity.Entity
    entity_temperature: appdaemon.entity.Entity
    entity_window: appdaemon.entity.Entity

    def initialize(self):
        self.entity_radiator = self.get_entity(self.args['entity_radiator'])
        self.entity_temperature = self.get_entity(self.args['entity_temperature'])
        self.entity_window = self.get_entity(self.args['entity_window'])

        for entity in (self.entity_radiator, self.entity_temperature, self.entity_window):
            if not entity.exists():
                self.logger.error('Entity %r not found.', entity.entity_id)
                return

        self.entity_window.listen_state(self.control_radiator)
        self.run_every(self.control_radiator, 'now + 4', PERIOD_MINUTES * 60)

    def control_radiator(self, *args, **kwargs):
        self.logger.debug('Evaluating radiator control for %r.', self.entity_radiator.entity_id)

        # stop heating if window is open:
        if self.entity_window.get_state() == 'on':
            self.logger.debug('Not heating because window is open.')
            self.set_temperature(0)
            return

        # check time if in eco or comfort mode:
        now = datetime.datetime.now().time()
        comfort_start_str = self.get_state(self.args['entity_time_comfort_start'])
        comfort_stop_str = self.get_state(self.args['entity_time_comfort_stop'])

        if not (comfort_start_str and comfort_stop_str):
            self.logger.error('Not all switch times are defined.')
            return

        comfort_start = datetime.time.fromisoformat(comfort_start_str)
        comfort_stop = datetime.time.fromisoformat(comfort_stop_str)

        if comfort_start <= now < comfort_stop:
            self.logger.debug('Heating in comfort mode.')
            self.set_temperature(float(self.get_state(self.args['entity_temperature_comfort'])))
        else:
            self.logger.debug('Heating in eco mode.')
            self.set_temperature(float(self.get_state(self.args['entity_temperature_eco'])))

    def set_temperature(self, temperature: float):
        self.logger.debug('Setting target temperature to %s.', temperature)

        if temperature > 0:
            current_temperature = float(self.entity_temperature.get_state())
            apparent_temperature = float(self.entity_radiator.get_state('current_temperature'))
            target_temperature = temperature + 2 * (apparent_temperature - current_temperature)

            self.logger.debug('Offset correcting target temperature to %s.', target_temperature)
            self.entity_radiator.call_service('set_temperature', temperature=target_temperature)
        else:
            self.entity_radiator.call_service('set_temperature', hvac_mode='off', temperature=0)
