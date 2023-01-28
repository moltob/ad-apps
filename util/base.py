import appdaemon.plugins.hass.hassapi
import typing as t
import appdaemon.entity


class MyHomeAssistantApp(appdaemon.plugins.hass.hassapi.Hass):
    """Base class exposing some utilities for AppDaemon apps."""

    async def initialize(self):
        """Initialize entities of derived class.

        Derived class is expected to define annotated attributes of type Entity, which are found in
        thiis method and then their name is looked up in the app's argument dictionary. The value
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
