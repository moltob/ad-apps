"""Toogle an entity after a switch was pushed."""

import datetime

import appdaemon.entity
import appdaemon.plugins.mqtt.mqttapi

from util.base import MyHomeAssistantApp

MQTT_PLUGIN_NAMESPACE = 'mqtt'
"""Namespace of the AD MQTT plugin, set in `appdaemon.yaml`."""


class MqttActionAdapterApp(appdaemon.plugins.mqtt.mqttapi.Mqtt):
    """Adapter converting MQTT-action messages to callbacks.

    Z2M 2.0.0 is removing the kegacy action entity which therefore can no longer be monitored for
    state changes, as that change would possible not change on repeatedly pressing the same button.

    The documented approach of using device triggers is (a) depending on opaque hex device IDs and
    (b) not supported by AddDaemon of of today.

    As a "workaround" listen to MQTT topics and convert them to callbacks that were previously
    triggered by action entity changes.
    """

    topic: str | None = None

    async def initialize(self, *, sensor: appdaemon.entity.Entity, action: str, callback):
        friendly_name = sensor.friendly_name
        suffix = ' Action'

        if not friendly_name.endswith(suffix):
            self.logger.error(
                'MQTT adapter can only adapt action entities, but name of %r does not end with %r. '
                'Skipping.',
                friendly_name,
                suffix,
            )
            return

        async def _callback(*args, **kwargs):
            await callback()

        self.topic = f'zigbee2mqtt/{friendly_name[: -len(suffix)]}/action'
        self.mqtt_subscribe(self.topic, namespace=MQTT_PLUGIN_NAMESPACE)
        await self.listen_event(
            _callback,
            'MQTT_MESSAGE',
            namespace=MQTT_PLUGIN_NAMESPACE,
            payload=action,
        )

    async def terminate(self):
        if self.topic:
            self.mqtt_unsubscribe(self.topic, namespace=MQTT_PLUGIN_NAMESPACE)
            self.topic = None


class ActionToggleApp(MyHomeAssistantApp):
    """A toggle exposing an action."""

    ent_sensor: appdaemon.entity.Entity
    ent_actuator: appdaemon.entity.Entity

    legacy_action: bool

    action_adapter: MqttActionAdapterApp

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.action_adapter = MqttActionAdapterApp(*args, **kwargs)

    async def initialize(self):
        await super().initialize()

        self.legacy_action = self.args.get('legacy_action', False)

        self.logger.info(
            'Binding switch %r to actuator %r.',
            self.ent_sensor.entity_id,
            self.ent_actuator.entity_id,
        )

        sensor_action = self.args.get('sensor_action', 'single')
        if self.legacy_action:

            async def toggle_actuator(self, entity, attribute, old, new, *args, **kwargs):
                await self.toggle_actuator()

            await self.ent_sensor.listen_state(toggle_actuator, sensor_action)
        else:
            await self.action_adapter.initialize(
                sensor=self.ent_sensor, action=sensor_action, callback=self.toggle_actuator
            )

    async def toggle_actuator(self):
        self.logger.info(
            '%r was pushed, toggeling %r. Current state was %r.',
            self.ent_sensor.name,
            self.ent_actuator.name,
            await self.ent_actuator.get_state(),
        )
        await self.ent_actuator.toggle()

    async def terminate(self):
        if not self.legacy_action:
            await self.action_adapter.terminate()
        await super().terminate()


class WelcomeLightApp(MyHomeAssistantApp):
    """Turn on light at arrival."""

    ent_light: appdaemon.entity.Entity
    ent_persons: list[appdaemon.entity.Entity]

    async def initialize(self):
        await super().initialize()

        for person in self.ent_persons:
            await person.listen_state(self.turn_lights_on, new='home')
            self.logger.info('Binding welcome light to arrival of %r.', person.entity_id)

        self.logger.info('Next sunset is at %s.', await self.sunset(aware=True))

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

        actions = self.args.get('actions', {})
        action_single = actions.get('single', 'single')
        action_double = actions.get('double', 'double')

        await self.ent_switch.listen_state(self.switch_to_next_light, new=action_single)
        await self.ent_switch.listen_state(self.toggle_all_lights, new=action_double)

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


class TimerApp(MyHomeAssistantApp):
    """Switch off an entity after timeout."""

    ent_actuator: appdaemon.entity.Entity

    timeout: datetime.timedelta
    timeout_handle: str | None

    async def initialize(self):
        await super().initialize()

        self.timeout = datetime.timedelta(minutes=float(self.args['minutes']))
        self.timeout_handle = None

        self.logger.info(
            'Observing actuator %r and will disable after %.1f minutes.',
            self.ent_actuator.entity_id,
            self.timeout.total_seconds() / 60,
        )

        await self.ent_actuator.listen_state(self.actuator_turned_on, new='on')
        await self.ent_actuator.listen_state(self.actuator_turned_off, new='off')
        await self.ent_actuator.listen_state(self.actuator_turned_off, new='unavailable')

    async def actuator_turned_on(self, *args, **kwargs):
        self.logger.info('%r was turned on.', self.ent_actuator.entity_id)
        self.timeout_handle = await self.run_in(self.timeout_expired, self.timeout.total_seconds())

    async def timeout_expired(self, *args, **kwargs):
        self.logger.info('Timeout expired turning off %r.', self.ent_actuator.entity_id)
        self.timeout_handle = None
        await self.ent_actuator.turn_off()

    async def actuator_turned_off(self, *args, **kwargs):
        self.logger.info('%r was turned off.', self.ent_actuator.entity_id)

        if self.timeout_handle:
            await self.cancel_timer(self.timeout_handle)
            self.timeout_handle = None
