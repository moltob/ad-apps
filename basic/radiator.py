"""Basic radiator control through external temperature sensor."""
import datetime
import typing as t

import appdaemon.plugins.hass.hassapi

PERIOD_MINUTES = 15


class MyHomeAssistantApp(appdaemon.plugins.hass.hassapi.Hass):
    """Base class exposing some utilities for AppDaemon apps.

    For convenience, some wrappers for base class methods are offered in an "ae" version, meaning
    they take the entity ID as indirect reference by an app argument.
    """

    def get_state_ae(self, argument_name: str, *args, **kwargs) -> str:
        return t.cast(str, self.get_state(self.args[argument_name], *args, **kwargs))

    def call_service_ae(self, service: str, argument_name: str, **kwargs):
        self.call_service(service, entity_id=self.args[argument_name], **kwargs)


class RadiatorApp(MyHomeAssistantApp):
    def initialize(self):
        self.listen_state(self.control_radiator, self.args['entity_window'])
        self.run_every(self.control_radiator, 'now + 5', PERIOD_MINUTES * 60)

    def control_radiator(self, *args, **kwargs):
        # stop heating if window is open:
        if self.get_state_ae('entity_window') == 'on':
            self.set_temperature(0, 'Window open')
            return

        # check time if in eco or comfort mode:
        now = datetime.datetime.now().time()
        comfort_start = datetime.time.fromisoformat(self.get_state_ae('entity_time_comfort_start'))
        comfort_stop = datetime.time.fromisoformat(self.get_state_ae('entity_time_comfort_stop'))

        if comfort_start <= now < comfort_stop:
            self.set_temperature(
                float(self.get_state_ae('entity_temperature_comfort')), 'Comfort mode'
            )
        else:
            self.set_temperature(float(self.get_state_ae('entity_temperature_eco')), 'Eco mode')

    def set_temperature(self, target_temperature: float, reason: str):
        apparent_temperature = float(self.get_state_ae('entity_radiator', 'current_temperature'))
        actual_temperature = float(self.get_state_ae('entity_temperature'))

        if target_temperature > 0 and actual_temperature < target_temperature:
            offset = max(0.0, 2 * (apparent_temperature - actual_temperature))
            set_temperature = target_temperature + offset
        else:
            set_temperature = 0

        self.logger.info(
            '%s: target = %s, apparent = %s, actual = %s, set = %s.',
            reason,
            target_temperature,
            apparent_temperature,
            actual_temperature,
            set_temperature,
        )

        self.call_service_ae(
            'climate/set_temperature',
            'entity_radiator',
            temperature=set_temperature,
        )
