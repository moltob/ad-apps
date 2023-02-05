"""Toogle an entity after a switch was pushed."""
import appdaemon.entity

from util.base import MyHomeAssistantApp


class ActionToggleApp(MyHomeAssistantApp):
    """A toggle exposing an action."""

    ent_sensor: appdaemon.entity.Entity
    ent_actuator: appdaemon.entity.Entity

    async def initialize(self):
        await super().initialize()

        self.logger.info(
            'Binding switch %r to actuator %r.',
            self.ent_sensor.entity_id,
            self.ent_actuator.entity_id,
        )
        await self.ent_sensor.listen_state(
            self.toggle_actuator, new=self.args.get('sensor_action', 'single')
        )

    async def toggle_actuator(self, entity, attribute, old, new, kwargs):
        await self.ent_actuator.toggle()
