"""Watchdog observing last_seen attribute of sensors."""

import datetime

import appdaemon.entity
import appdaemon.plugins.mqtt.mqttapi

from util.base import MyHomeAssistantApp


class LastSeenApp(appdaemon.plugins.mqtt.mqttapi.Mqtt):
    """Watchdog of last_seen attribute of sensors.

    If a sensor has not been seen for a configurable amount of time, a notification is raised. Note
    that this is a real error condition, as usually unexpected, e.g. after power loss.

    This might happen unnoticed for MQTT-based entities.

    Remarks:

        The code below requires that the last_seen entities are enabled. Unfortunately, they are disabled by
        default.

        Docs usggest to use device availability instead. But this does not work, the device appears to be available...

    """

    expiration_hours: int

    async def initialize(self):
        # await super().initialize()

        self.mqtt_subscribe('zigbee2mqtt/+/availability', namespace='mqtt')
        await self.listen_event(
            self.check_entities,
            'MQTT_MESSAGE',
            namespace='mqtt',
            wildcard='zigbee2mqtt/+/availability',
            payload='{"state":"offline"}',
        )

    async def check_entities(self, *args, **kwargs):
        self.logger.debug(args, kwargs)

    async def terminate(self):
        self.mqtt_unsubscribe('zigbee2mqtt/+/availability', namespace='mqtt')
