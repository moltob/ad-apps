"""Toogle an entity after a switch was pushed."""
import appdaemon.plugins.hass.hassapi
import appdaemon.entity

from util.base import MyHomeAssistantApp


class ToggleApp(MyHomeAssistantApp):
    def initialize(self):
        self.logger.info(
            'Binding switch %r to actuator %r.',
            self.args['entity_sensor'],
            self.args['entity_actuator'],
        )
        self.listen_state_ae(self.toggle_actuator, 'entity_sensor', new='single')

    def toggle_actuator(self, entity, attribute, old, new, kwargs):
        self.entity_actuator.toggle()
