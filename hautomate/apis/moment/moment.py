import time

import pendulum

from hautomate.api import API


class Moment(API):
    """


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
