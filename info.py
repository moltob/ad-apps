"""Collect info about HA system and provide it as helper entities."""

import datetime

import appdaemon.entity
import appdaemon.plugins.hass.hassapi
from config.apps.util.base import MyHomeAssistantApp


class InfoApp(MyHomeAssistantApp):
    """Collect system information and write it to helper entities.

    For physical data, use sensor entities, for abstract data use input helpers. See also:
    https://community.home-assistant.io/t/sensor-creation/39503.
    """

    entity_batteries: appdaemon.entity.Entity

    async def initialize(self):
        await super().initialize()

        # compute entities on startup and then once a day:
        self.run_in(self.update_helper_entities, 0)
        self.run_daily(self.update_helper_entities, datetime.time(3))

    async def update_helper_entities(self, kwargs):
        battery_entity_ids = [
            s['entity_id']
            for s in (await self.get_state()).values()
            if (c := s['attributes'].get('device_class')) and (c == 'battery')
        ]

        self.logger.info(
            'Setting batteries entity %r to: %r',
            self.entity_batteries,
            ', '.join(battery_entity_ids),
        )
        await self.entity_batteries.set_state(state=battery_entity_ids)
