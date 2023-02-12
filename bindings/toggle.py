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
        self.logger.info(
            '%r was pushed, toggeling %r.',
            self.ent_sensor.name,
            self.ent_actuator.name,
        )
        await self.ent_actuator.toggle()


class WelcomeLightApp(MyHomeAssistantApp):
    """Turn on light at arrival."""

    ent_light: appdaemon.entity.Entity
    ent_person_1: appdaemon.entity.Entity
    ent_person_2: appdaemon.entity.Entity

    async def initialize(self):
        await super().initialize()

        for person in (self.ent_person_1, self.ent_person_2):
            await person.listen_state(self.turn_lights_on, new='home')
            self.logger.info('Binding welcome light to arrival of %r.', person.name)

        await self.listen_application_trigger_event(self.turn_lights_on)

    async def turn_lights_on(self, *args, **kwargs):
        if args:
            self.logger.info('Welcome %r.', args[0])

        await self.ent_light.turn_on(effect='breathe')
        await self.sleep(3)
        await self.ent_light.turn_on(effect='finish_effect')
