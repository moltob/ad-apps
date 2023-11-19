"""Watchdog observing device status."""

import datetime

import appdaemon.entity
import appdaemon.plugins.mqtt.mqttapi

from util.base import MyHomeAssistantApp

TOPIC = 'zigbee2mqtt/+/availability'
"""Topic yielding devices' availability status."""


PLUGIN_NAMESPACE = 'mqtt'
"""Namespace of the AD MQTT plugin, set in `appdaemon.yaml`."""

MQTT_EVENT_NAME = 'MQTT_MESSAGE'
"""Name of MQTT message events."""

DEVICE_OFFLINE_PAYLOAD = '{"state":"offline"}'
"""Event payload of an offline device."""


class NotifyOfflineApp(appdaemon.plugins.mqtt.mqttapi.Mqtt):
    """Watchdog detecting offline Zigbee2Mqtt devices.

    In order for this to work, Z2M must be configured to detect and subsequentially provide device
    availability, see https://www.zigbee2mqtt.io/guide/configuration/device-availability.html.
    """

    async def initialize(self):
        self.mqtt_subscribe(TOPIC, namespace=PLUGIN_NAMESPACE)
        await self.listen_event(
            self.report_offline_entities,
            MQTT_EVENT_NAME,
            namespace=PLUGIN_NAMESPACE,
            wildcard=TOPIC,
            payload=DEVICE_OFFLINE_PAYLOAD,
        )

    async def report_offline_entities(self, event, data, *args, **kwargs):
        if not (topic := data.get('topic')):
            self.logger.error(
                'Dropping unexpected event: event=%r, data=%r, args=%r, kwargs=%r',
                event,
                data,
                args,
                kwargs,
            )
            return

        self.logger.debug('Received offline availability for %r.', topic)

        parts = topic.split('/')
        if len(parts) != 3:
            self.logger.error('Found unexpected number of topic separators in %r.', topic)
            return

        assert topic.count('/') == 2, 'unexpected number of topic separators, adapt assert/split'

        device = parts[1]
        self.logger.info('Device %r is offline.', device)

        service = self.args['notify'].get('service', 'notify')
        await self.call_service(
            f'notify/{service}',
            title='Zigbee device availability',
            message=f'{device!r} is no longer online.',
        )

    async def terminate(self):
        self.mqtt_unsubscribe(TOPIC, namespace=PLUGIN_NAMESPACE)
