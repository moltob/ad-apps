import typing as t

import appdaemon.entity
import appdaemon.plugins.hass.hassapi


class MyHomeAssistantApp(appdaemon.plugins.hass.hassapi.Hass):
    """Base class exposing some utilities for AppDaemon apps."""

    trigger_dispatch_table: dict[str, t.Callable] = {}
    trigger_handle = None

    async def initialize(self):
        """Initialize entities of derived class.

        Derived class is expected to define annotated attributes of type Entity, which are found in
        this method and then their name is looked up in the app's argument dictionary. The value
        there is then used as entity ID, which in turn results of a member attribute for that
        entity.
        """
        entity_id_by_key = self.args['entities']
        for key, type_ in self.__annotations__.items():
            if type_ == appdaemon.entity.Entity:
                if not (entity_id := entity_id_by_key.get(key)):
                    self.logger.error(
                        'App configuration YAML does not define required entity %r in entities '
                        'dictionary.',
                        key,
                    )
                    continue

                entity = self.get_entity(entity_id)

                self.logger.debug('Initializing entity %r.', entity_id)
                setattr(self, key, entity)

                if not await entity.exists():
                    self.logger.warning(
                        'Entity %r not found (passed to app through %r).',
                        entity_id,
                        key,
                    )

        # prepare for applications to dispatch triggers to if not done before, race conditions not
        # possible during initialization as those functions are called synchronously:
        if not MyHomeAssistantApp.trigger_handle:
            MyHomeAssistantApp.trigger_handle = await self.listen_event(
                self._dispatch_trigger_to_app,
                'ad_trigger',
            )

    async def terminate(self):
        # all events are cancelled, so we have to reregister during next initialization:
        MyHomeAssistantApp.trigger_handle = None

    async def _dispatch_trigger_to_app(self, event_name: str, data: dict, kwargs):
        if not (app_name := data.get('name')):
            self.logger.error('Received app trigger, but name is missing.')
            return

        if not (callback := self.trigger_dispatch_table.get(app_name)):
            self.logger.error('Received app trigger for unregistered application %r.', app_name)
            return

        # propagate the trigger to application instance:
        await callback()

    def listen_application_trigger_event(self, callback: t.Callable):
        """Register for callback into given callable."""
        self.trigger_dispatch_table[self.name] = callback
