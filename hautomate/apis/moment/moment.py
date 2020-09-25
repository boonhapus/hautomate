from typing import Union, Callable
import datetime as dt
import asyncio
import logging
import time

import pendulum

from hautomate.apis.moment.checks import MomentaryCheck
from hautomate.apis.moment.events import EVT_TIME_UPDATE, EVT_TIME_SLIPPAGE
from hautomate.util.async_ import safe_sync
from hautomate.context import Context
from hautomate.intent import Intent
from hautomate.check import Throttle
from hautomate.api import API, api_method, public_method


_log = logging.getLogger(__name__)


class Moment(API):
    """
    API for working with absolute and relative dates and times.

    Parameters
    ----------
    hauto : HAutomate
      hautomate!

    resolution : float = 0.25
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
        self.resolution = resolution
        self.speed = speed
        self.epoch = epoch or pendulum.now(tz=hauto.config.timezone)
        self._monotonic_epoch = time.perf_counter()
        super().__init__(hauto)

    # Listeners and Internal Methods

    @safe_sync
    def on_ready(self, ctx: Context):
        """
        Called once HAutomate is ready to begin processing events.
        """
        asyncio.create_task(self._tick())

    async def _tick(self):
        """
        Internal heartbeat to determine the health of HAutomate.
        """
        while self.hauto.is_ready:
            asyncio.create_task(self.fire(EVT_TIME_UPDATE))
            beg = self.hauto.loop.time()
            await asyncio.sleep(self.resolution)
            end = self.hauto.loop.time()
            lag = (end - beg)

            if lag > (self.resolution + 0.1):
                _log.warning(f'lag of {lag :.6f}s, {round(lag * 1000)}ms')
                coro = self.fire(EVT_TIME_SLIPPAGE, lag=lag)
                asyncio.create_task(coro)

    # Public Methods

    @public_method
    @safe_sync
    def now(self) -> pendulum.DateTime:
        """
        Return the current time.
        """
        elapsed = time.perf_counter() - self._monotonic_epoch
        return self.epoch.add(seconds=elapsed * self.speed)

    @public_method
    @safe_sync
    def scale_time(self, seconds: float, *, to: str='realtime') -> float:
        """
        Convert the input time to real or virtual time.

        This is mainly used for interacting with time based systems
        outside of HAutomate.

        Parameters
        ----------
        seconds : float
          amount of time to scale

        to : str = 'realtime'
          which direction to scale to, realtime or virtual

        Returns
        -------
        scaled : float
        """
        _directions = {
            'realtime': seconds / self.speed,
            'virtual': seconds * self.speed
        }

        try:
            return _directions[to.lower()]
        except KeyError:
            m = f"keyword argument must be one of: 'realtime' or 'virtual', got: {to}"
            raise ValueError(m) from None

    # Intents

    @api_method
    def at(
        self,
        when: Union[pendulum.DateTime, str, int],
        *,
        fn: Callable,
        **intent_kwargs
    ) -> Intent:
        """
        Wait to fire until a specific moment.

        Can be used as an App function decorator. If used inline, this
        method expects a keyword argument 'fn', the intended method to
        call upon meeting the criteria. All other keyword arguments are
        passed into the Intent.

        Parameters
        ----------
        when : pendulum.DateTime, str, or int
            time at which to fire the Intent
                this parameter may come in one of a few forms:
                - datetime.datetime or pendulum.DateTime
                - a datetime or time parseable string
                    - dates follow format: YYYY/MM/DD
                    - times follow format: HH:MM:SS
                - a UNIX timestamp

        Returns
        -------
        intent : Intent
        """
        try:
            intent_kwargs['checks']
        except KeyError:
            intent_kwargs['checks'] = []

        if isinstance(when, (dt.datetime, int)):
            try:
                when = when.timestamp()
            except AttributeError:
                pass

            # ensure pendulum.DateTime
            when = pendulum.from_timestamp(when, tz='UTC')

            intent_kwargs['limit'] = intent_kwargs.get('limit', 1)
            intent_kwargs['checks'].append(MomentaryCheck(when))
            intent = Intent(EVT_TIME_UPDATE, fn=fn, **intent_kwargs)
        else:
            # str parsing
            dattim = pendulum.parse(str(when), exact=True)

            if isinstance(dattim, pendulum.Date):
                # conversion to DateTime will mean YYYY/MM/DD 00:00:00
                when = pendulum.parse(f'{dattim} 00:00:00', tz='UTC')
                intent_kwargs['checks'].append(MomentaryCheck(when))

            if isinstance(dattim, pendulum.Time):
                # recurrence at a specific time
                intent_kwargs['checks'].append(MomentaryCheck(dattim))

            intent = Intent(EVT_TIME_UPDATE, fn=fn, **intent_kwargs)

        return intent

    @api_method
    def soon(
        self,
        delay: Union[float, pendulum.Duration]=0,
        *,
        fn: Callable,
        **intent_kwargs
    ) -> Intent:
        """
        Schedule an Intent to run after a short duration.

        Can be used as an App function decorator. If used inline, this
        method expects a keyword argument 'fn', the intended method to
        call upon meeting the criteria. All other keyword arguments are
        passed into the Intent.

        Parameters
        ----------
        delay : float or pendulum.Duration, default 0 seconds
            amount of time to wait before firing

        Returns
        -------
        intent : Intent
        """
        # TODO: figure out how to handle these formats, all mean 5 minutes
        # '5:00'
        # '5:00'
        # '5 minutes'
        # '5 min'
        # '5m'
        try:
            delay = delay.total_seconds()
        except AttributeError:
            pass

        if not isinstance(delay, (float, int)):
            raise ValueError(f"'delay' must be of type float, got: {type(delay)}")

        when = self.hauto.now.add(seconds=delay)
        return self.at(when, fn=fn, **intent_kwargs)

    @api_method
    def every(
        self,
        delta: Union[float, pendulum.Duration],
        *,
        when: pendulum.DateTime=-1,
        fn: Callable, **intent_kwargs
    ) -> Intent:
        """
        Schedule an Intent to run after a short duration.

        Can be used as an App function decorator. If used inline, this
        method expects a keyword argument 'fn', the intended method to
        call upon meeting the criteria. All other keyword arguments are
        passed into the Intent.

        Parameters
        ----------
        delta : float or pendulum.Duration
            amount of time to wait between intent fires

        when : pendulum.DateTime, default is a magic value for now
            first time this intent should fire

        Returns
        -------
        intent : Intent
        """
        # TODO: figure out how to handle these formats, all mean 5 minutes
        # '5:00'
        # '5:00'
        # '5 minutes'
        # '5 min'
        # '5m'
        try:
            intent_kwargs['checks']
        except KeyError:
            intent_kwargs['checks'] = []

        if isinstance(delta, dt.timedelta):
            cooldown = Throttle(delta.total_seconds())
        elif isinstance(delta, (float, int)):
            cooldown = Throttle(delta)
        else:
            raise TypeError(f"'delta' must be of type float, got: '{delta}'")

        intent_kwargs['checks'].append(cooldown)
        intent_kwargs['limit'] = intent_kwargs.get('limit', -1)
        return self.at(when, fn=fn, **intent_kwargs)
