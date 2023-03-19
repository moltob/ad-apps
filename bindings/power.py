"""Observe power consumption of a device."""
import datetime
import appdaemon.entity

from util.base import MyHomeAssistantApp


class PowerObserverApp(MyHomeAssistantApp):
    ent_power: appdaemon.entity.Entity

    power_min: float
    power_max: float
    power_duration: datetime.timedelta

    interval_entered: datetime.datetime | None
    interval_notified: bool

    async def initialize(self):
        await super().initialize()

        self.power_min = float(self.args['power']['min'])
        self.power_max = float(self.args['power']['max'])
        self.power_duration = datetime.timedelta(minutes=float(self.args['power']['minutes']))

        self.logger.info(
            'Target interval [%.2f, %.2f] must be entered for %.2f seconds.',
            self.power_min,
            self.power_max,
            self.power_duration.seconds,
        )

        self.interval_entered = None
        self.interval_notified = False
        await self.ent_power.listen_state(self.process_power_change)

    async def process_power_change(self, entity, attribute, old, new, *args, **kwargs):
        power = float(new)
        self.logger.debug('Power changed to %.2f W.', power)

        if self.interval_notified:
            if power > self.power_max:
                self.logger.info('Resetting for new cycle.')
                self.interval_notified = False
                return

        if not self.interval_entered:
            if self.power_min <= power <= self.power_max:
                self.logger.debug('Entering target power interval.')
                self.interval_entered = datetime.datetime.now()
        else:
            # we get a new value on change only, so once we are beyond the interval, we can fire:
            if (datetime.datetime.now() - self.interval_entered) >= self.power_duration:
                self.logger.info('Target interval entered long enough for trigger condition.')
                self.interval_notified = True
                await self.call_service(
                    "notify/notify",
                    title=self.args['notify']['title'],
                    message=self.args['notify']['message'],
                )
            else:
                self.logger.debug('Leaving target interval.')
                self.interval_entered = None
