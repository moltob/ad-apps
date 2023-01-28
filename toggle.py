"""Toogle an entity after a switch was pushed."""
import appdaemon.entity

from config.apps.util.base import MyHomeAssistantApp


class ToggleApp(MyHomeAssistantApp):
    entity_sensor: appdaemon.entity.Entity
    entity_actuator: appdaemon.entity.Entity

    async def initialize(self):
        await super().initialize()

        self.logger.info(
            'Binding switch %r to actuator %r.',
            self.entity_sensor.entity_id,
            self.entity_actuator.entity_id,
        )
        await self.entity_sensor.listen_state(self.toggle_actuator, new='single')

    async def toggle_actuator(self, entity, attribute, old, new, kwargs):
        await self.entity_actuator.toggle()
