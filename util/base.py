import appdaemon.plugins.hass.hassapi
import typing as t


PERIOD_MINUTES = 15


class MyHomeAssistantApp(appdaemon.plugins.hass.hassapi.Hass):
    """Base class exposing some utilities for AppDaemon apps.

    For convenience, some wrappers for base class methods are offered in an "ae" version, meaning
    they take the entity ID as indirect reference by an app argument.
    """

    def listen_state_ae(self, callback, argument_name: str, **kwargs):
        return self.listen_state(callback, self.args[argument_name], **kwargs)

    def get_state_ae(self, argument_name: str, *args, **kwargs) -> str:
        return t.cast(str, self.get_state(self.args[argument_name], *args, **kwargs))

    def call_service_ae(self, service: str, argument_name: str, **kwargs):
        self.call_service(service, entity_id=self.args[argument_name], **kwargs)
