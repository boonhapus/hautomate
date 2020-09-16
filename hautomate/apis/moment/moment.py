import asyncio
import logging
import time

import pendulum

from hautomate.apis.moment.events import EVT_TIME_UPDATE, EVT_TIME_SLIPPAGE
from hautomate.context import Context
from hautomate.api import API


_log = logging.getLogger(__name__)


class Moment(API):
    """
    API for working with absolute and relative dates and times.

    Parameters
    ----------
    hauto : HAutomate
      hautomate!

    resolution : float = 1.0
      number of seconds between TIME_UPDATE events

    speed : float = 1.0
      factor at which time passes every iteration, default is 1.0 or realtime

    epoch : pendulum.DateTime = None
      start of the virtual clock, default is None, to mean no initial skew
    """
    def __init__(
        self,
        hauto,
        *,
        resolution: float=0.25,
        speed: float=1.00,
        epoch: pendulum.DateTime=None
    ):
        super().__init__(hauto)
        self.resolution = resolution
        self.speed = speed
        self.epoch = epoch or pendulum.now(tz=hauto.config.timezone)
        self._monotonic_epoch = time.perf_counter()

    @property
    def now(self) -> pendulum.DateTime:
        """
        Return the current time.
        """
        elapsed = time.perf_counter() - self._monotonic_epoch
        return self.epoch.add(seconds=elapsed * self.speed)

    # Listeners and Internal Methods

    async def on_ready(self, ctx: Context):
        """
        Called once HAutomate is ready to begin processing events.
        """
        asyncio.create_task(self._tick())

    async def _tick(self):
        """
        Internal heartbeat to determine the health of HAutomate.
        """
        while not self.hauto.is_ready:
            asyncio.create_task(self.fire(EVT_TIME_UPDATE))
            before = self.hauto.loop.time()
            await asyncio.sleep(self.resolution)
            after = self.hauto.loop.time()
            lag = (after - before) - 1

            if lag >= self.resolution:
                _log.warning(f'lag of {lag :.6f}s, {round(lag * 1000)}ms')
                coro = self.fire(EVT_TIME_SLIPPAGE, lag=lag)
                asyncio.create_task(coro)

    # Public Methods

    def scale_to_realtime(self, seconds: float) -> float:
        """
        Convert the input time, scaled by the time factor in HAutomate.

        This is mainly used for interacting with time based systems
        outside of HAutomate.
        """
        return seconds / self.speed
