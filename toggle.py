"""Toogle an entity after a switch was pushed."""
import appdaemon.plugins.hass.hassapi
import appdaemon.entity


class ToggleApp(appdaemon.plugins.hass.hassapi.Hass):
    entity_sensor: appdaemon.entity.Entity
    entity_actuator: appdaemon.entity.Entity

    def initialize(self):
        self.entity_sensor = self.get_entity(self.args['entity_sensor'])
        self.entity_actuator = self.get_entity(self.args['entity_actuator'])

        if not self.entity_sensor.exists():
            self.logger.error('Sensor entity %r does not exist.', self.entity_sensor.entity_id)
            return

        if not self.entity_actuator.exists():
            self.logger.error('Actuator entity %r does not exist.', self.entity_actuator.entity_id)
            return

        self.logger.info(
            'Binding sensor %r to actuator %r.',
            self.entity_sensor.entity_id,
            self.entity_actuator.entity_id,
        )
        self.entity_sensor.listen_state(self.toggle_actuator, new='single')

    def toggle_actuator(self, entity, attribute, old, new, kwargs):
        self.logger.debug('Toggle %r.', self.entity_actuator.entity_id)
        self.entity_actuator.toggle()
