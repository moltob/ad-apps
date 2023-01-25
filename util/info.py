"""Collect info about HA system and provide it as helper entities."""

import datetime

import appdaemon.plugins.hass.hassapi
import appdaemon.entity

BATTERY_ENTITIES_HELPER_NAME = 'input_text.mike_storage'


class InfoApp(appdaemon.plugins.hass.hassapi.Hass):
    """Collect system information and write it to helper entities.

    For physical data, use sensore entities, for abstract data use input helpers. See also:
    https://community.home-assistant.io/t/sensor-creation/39503.
    """

    battery_entities_helper: appdaemon.entity.Entity = None

    def initialize(self):
        # compute entities on startup and then once a day:
        self.run_in(self.update_helper_entities, 0)
        self.run_daily(self.update_helper_entities, datetime.time(3))

    def update_helper_entities(self, kwargs):
        self.logger.info('Recomputing information helper entities.')

        if not self.battery_entities_helper:
            self.logger.debug(
                'Attempting to get existing battery entities helper %r.',
                BATTERY_ENTITIES_HELPER_NAME,
            )
            self.battery_entities_helper = self.get_entity(BATTERY_ENTITIES_HELPER_NAME)

            if self.battery_entities_helper.exists():
                self.logger.debug('Entity found.')
            else:
                self.logger.info('Entity not found, will create it.')

        battery_entity_ids = [
            s['entity_id']
            for s in self.get_state().values()
            if (c := s['attributes'].get('device_class')) and (c == 'battery')
        ]
        self.logger.info('Found battery entities: %r', ', '.join(battery_entity_ids))

        self.battery_entities_helper.set_state(state=battery_entity_ids)
