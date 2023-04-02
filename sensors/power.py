"""Observe power consumption of a device."""
import datetime
import enum
import appdaemon.entity

from util.base import MyHomeAssistantApp


class DeviceState(enum.Enum):
    OFF = 'Off'
    RUNNING = 'Running'
    ALMOST_DONE = 'Almost Done'


class PowerObserverApp(MyHomeAssistantApp):
    ent_power: appdaemon.entity.Entity

    power_active: float
    power_done: float
    duration_done: datetime.timedelta

    state: DeviceState
    state_entered: datetime.datetime

    done_timer_handle: str | None

    async def initialize(self):
        await super().initialize()

        self.power_active = float(self.args['power']['active'])
        self.power_done = float(self.args['power']['done'])
        self.duration_done = datetime.timedelta(minutes=float(self.args['power']['duration_done']))

        self.state = DeviceState.OFF
        self.state_entered = datetime.datetime.now()
        self.done_timer_handle = None

        await self.ent_power.listen_state(self.process_power_change)

    async def _enter_state(self, state: DeviceState, power: float):
        # switching state will cancel the timer if running:
        if self.done_timer_handle:
            await self.cancel_timer(self.done_timer_handle)
            self.done_timer_handle = None

        self.logger.info(
            'Switching from state %r to %r at %.2f W.',
            self.state.value,
            state.value,
            power,
        )

        self.state = state
        self.state_entered = datetime.datetime.now()

    async def process_power_change(self, entity, attribute, old, new, *args, **kwargs):
        power = float(new)
        now = datetime.datetime.now()

        self.logger.debug('Power changed to %.2f W.', power)
        if power > 3500:
            self.logger.warning(
                'Power value %.2f ignored as it is out of reasonable operation range.',
                power,
            )
            return

        async def notify_done(app_, **kwargs):
            self.logger.info('Target interval entered long enough for trigger condition.')
            await self._enter_state(DeviceState.OFF, power)

            service = self.args['notify'].get('service', 'notify')
            await self.call_service(
                f'notify/{service}',
                title=self.args['notify']['title'],
                message=self.args['notify']['message'],
            )

        match self.state:
            case DeviceState.OFF:
                if power > self.power_active:
                    await self._enter_state(DeviceState.RUNNING, power)

            case DeviceState.RUNNING:
                if power <= self.power_done:
                    await self._enter_state(DeviceState.ALMOST_DONE, power)
                    self.done_timer_handle = await self.run_in(
                        notify_done,
                        self.duration_done.total_seconds(),
                    )

            case DeviceState.ALMOST_DONE:
                if power > self.power_done:
                    await self._enter_state(DeviceState.RUNNING, power)
