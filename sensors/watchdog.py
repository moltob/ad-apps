"""Watchdog observing device status."""

import datetime

import appdaemon.entity
import appdaemon.plugins.mqtt.mqttapi

from util.base import MyHomeAssistantApp

TOPIC = 'zigbee2mqtt/+/availability'
"""Topic yielding devices' availability status."""

PLUGIN_NAMESPACE = 'mqtt'
"""Namespace of the AD MQTT plugin, set in `appdaemon.yaml`."""

MQTT_EVEN_NAME = 'MQTT_MESSAGE'
"""Name of MQTT message events."""

DEVICE_UNAVAILABLE_PAYLOAD = '{"state":"offline"}'
"""Event payload of an offline device."""


class NotifyOfflineApp(appdaemon.plugins.mqtt.mqttapi.Mqtt):
    """Watchdog detecting offline Zigbee2Mqtt devices.

    In order for this to work, Z2M must be configured to detect and subsequentially provide device
    availability, see https://www.zigbee2mqtt.io/guide/configuration/device-availability.html.
    """

    async def initialize(self):
        # await super().initialize()

        self.mqtt_subscribe(TOPIC, namespace=PLUGIN_NAMESPACE)
        await self.listen_event(
            self.check_entities,
            MQTT_EVEN_NAME,
            namespace=PLUGIN_NAMESPACE,
            wildcard=TOPIC,
            payload=DEVICE_UNAVAILABLE_PAYLOAD,
        )

    async def check_entities(self, *args, **kwargs):
        self.logger.debug(args, kwargs)

    async def terminate(self):
        self.mqtt_unsubscribe(TOPIC, namespace=PLUGIN_NAMESPACE)
