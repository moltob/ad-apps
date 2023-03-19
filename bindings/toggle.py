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

    async def toggle_actuator(self, entity, attribute, old, new, *args, **kwargs):
        self.logger.info(
            '%r was pushed, toggeling %r.',
            self.ent_sensor.name,
            self.ent_actuator.name,
        )
        await self.ent_actuator.toggle()


class WelcomeLightApp(MyHomeAssistantApp):
    """Turn on light at arrival."""

    ent_light: appdaemon.entity.Entity
    ent_persons: list[appdaemon.entity.Entity]

    async def initialize(self):
        await super().initialize()

        for person in self.ent_persons:
            await person.listen_state(self.turn_lights_on, new='home')
            self.logger.info('Binding welcome light to arrival of %r.', person.entity_id)

        await self.listen_application_trigger_event(self.turn_lights_on)

    async def turn_lights_on(self, *args, **kwargs):
        if args:
            self.logger.info('Welcome %r.', args[0])

        await self.ent_light.turn_on(effect='breathe')
        await self.sleep(3)
        await self.ent_light.turn_on(effect='finish_effect')


class MultiLightToggleApp(MyHomeAssistantApp):
    """Control and toggle multiple lights with a single/double action switch.

    Single action toggles through the lights, turning on only one at a time. Double action will turn
    on/off all lights at once.
    """

    ent_lights: list[appdaemon.entity.Entity]
    ent_switch: appdaemon.entity.Entity

    async def initialize(self):
        await super().initialize()

        self.logger.info(
            'Binding switch %r to these lights: %s',
            self.ent_switch.entity_id,
            ', '.join(e.entity_id for e in self.ent_lights),
        )

        await self.ent_switch.listen_state(self.switch_to_next_light, new='single')
        await self.ent_switch.listen_state(self.toggle_all_lights, new='double')

    async def switch_to_next_light(self, entity, attribute, old, new, *args, **kwargs):
        if (current_index := await self.get_first_lit_index()) is not None:
            next_index = (current_index + 1) % len(self.ent_lights)
        else:
            next_index = 0

        next_light = self.ent_lights[next_index]
        self.logger.info('Switching light no. %d (%r).', next_index, next_light.entity_id)

        for light in self.ent_lights:
            if light is next_light:
                self.logger.debug('Switching on %r.', light.entity_id)
                await light.turn_on()
            else:
                self.logger.debug('Switching off %r.', light.entity_id)
                await light.turn_off()


    async def toggle_all_lights(self, entity, attribute, old, new, *args, **kwargs):
        if await self.get_first_lit_index() is None:
            service = 'turn_on'
        else:
            service = 'turn_off'

        self.logger.info('Invoking %r for all lights.', service)

        for light in self.ent_lights:
            await light.call_service(service)

    async def get_first_lit_index(self) -> int | None:
        """Return index of first light that is lit or None."""
        for index, light in enumerate(self.ent_lights):
            if await light.get_state() == 'on':
                return index

        # no light is lit:
        return None
