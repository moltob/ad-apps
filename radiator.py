"""Basic radiator control through external temperature sensor."""
import datetime

import appdaemon.entity

from config.apps.util.base import MyHomeAssistantApp

PERIOD_MINUTES = 15


class RadiatorApp(MyHomeAssistantApp):
    ent_radiator: appdaemon.entity.Entity
    ent_temperature: appdaemon.entity.Entity
    ent_window: appdaemon.entity.Entity
    ent_time_comfort_start: appdaemon.entity.Entity
    ent_time_comfort_stop: appdaemon.entity.Entity
    ent_temperature_comfort: appdaemon.entity.Entity
    ent_temperature_eco: appdaemon.entity.Entity

    async def initialize(self):
        await super().initialize()
        await self.ent_window.listen_state(self.control_radiator)
        await self.run_every(self.control_radiator, 'now + 5', PERIOD_MINUTES * 60)

    async def control_radiator(self, *args, **kwargs):
        # stop heating if window is open:
        if await self.ent_window.get_state() == 'on':
            await self.set_temperature(0, 'Window open')
            return

        # check time if in eco or comfort mode:
        now = datetime.datetime.now().time()
        comfort_start = datetime.time.fromisoformat(
            await self.ent_time_comfort_start.get_state()
        )
        comfort_stop = datetime.time.fromisoformat(await self.ent_time_comfort_stop.get_state())

        if comfort_start <= now < comfort_stop:
            await self.set_temperature(
                float(await self.ent_temperature_comfort.get_state()), 'Comfort mode'
            )
        else:
            await self.set_temperature(
                float(await self.ent_temperature_eco.get_state()), 'Eco mode'
            )

    async def set_temperature(self, target_temperature: float, reason: str):
        apparent_temperature = float(await self.ent_radiator.get_state('current_temperature'))
        actual_temperature = float(await self.ent_temperature.get_state())

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

        await self.ent_radiator.call_service('set_temperature', temperature=set_temperature)
