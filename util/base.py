import typing as t

import appdaemon.entity
import appdaemon.plugins.hass.hassapi


class MyHomeAssistantApp(appdaemon.plugins.hass.hassapi.Hass):
    """Base class exposing some utilities for AppDaemon apps."""

    app_trigger_dispatcher: t.Optional['AppTriggerDispatcher'] = None

    async def initialize(self):
        """Initialize entities of derived class.

        Derived class is expected to define annotated attributes of type Entity, which are found in
        this method and then their name is looked up in the app's argument dictionary. The value
        there is then used as entity ID, which in turn results of a member attribute for that
        entity.
        """
        if entity_id_by_key := self.args.get('entities'):
            for key, type_ in self.__annotations__.items():
                if type_ == appdaemon.entity.Entity:
                    if not (entity_id := entity_id_by_key.get(key)):
                        self.logger.error(
                            'App configuration YAML does not define required entity %r in entities '
                            'dictionary.',
                            key,
                        )
                        continue

                    setattr(self, key, await self._get_entity(key, entity_id))

                elif type_ == list[appdaemon.entity.Entity]:
                    if not (entity_ids := entity_id_by_key.get(key)):
                        self.logger.error(
                            'App configuration YAML does not define required entities list %r in '
                            'entities dictionary.',
                            key,
                        )
                        continue

                    setattr(
                        self,
                        key,
                        [await self._get_entity(key, entity_id) for entity_id in entity_ids],
                    )

    async def _get_entity(self, name: str, entity_id: str) -> appdaemon.entity.Entity:
        """Get entity with given ID from named argument."""
        entity = self.get_entity(entity_id)

        self.logger.debug('Initializing entity %r.', entity_id)

        if not await entity.exists():
            self.logger.warning(
                'Entity %r not found (passed to app through argument %r).',
                entity_id,
                name,
            )

        return entity

    async def terminate(self):
        # reference and event registration invalidated:
        self.app_trigger_dispatcher = None

    async def listen_application_trigger_event(self, callback: t.Callable):
        """Register for trigger callback into given application callable.

        This method must be called in a sequential way, i.e. during app initialization.
        """
        if not self.app_trigger_dispatcher:
            self.app_trigger_dispatcher = await self.get_app('dispatcher')

        await self.app_trigger_dispatcher.listen_application_trigger_event(self.name, callback)


class AppTriggerDispatcher(appdaemon.plugins.hass.hassapi.Hass):
    """Singleton application receiving application trigger events and dispatching them."""

    trigger_dispatch_table: dict[str, t.Callable]
    trigger_handle = None

    async def initialize(self):
        # listen to the generic application trigger event:
        self.trigger_dispatch_table = {}
        self.trigger_handle = await self.listen_event(
            self._dispatch_trigger_to_app,
            'ad_trigger',
        )

    async def terminate(self):
        # all events are cancelled, so we have to reregister during next initialization:
        self.trigger_handle = None

    async def listen_application_trigger_event(self, app_name: str, callback: t.Callable):
        """Register for trigger callback into given application callable."""
        # remember callback to invoke for current app:
        self.trigger_dispatch_table[app_name] = callback

    async def _dispatch_trigger_to_app(self, event_name: str, data: dict, kwargs):
        if not (app_name := data.get('name')):
            self.logger.error('Received app trigger, but name is missing in event data: %r', data)
            return

        if not (callback := self.trigger_dispatch_table.get(app_name)):
            self.logger.error('Received app trigger for unregistered application %r.', app_name)
            return

        # propagate the trigger to application instance:
        await callback()
