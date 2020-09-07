from typing import Callable
import asyncio

import pendulum

from hautomate.util.async_ import Asyncable, safe_sync
from hautomate.errors import HautoException
from hautomate.context import Context


class Check(Asyncable):
    """
    A non-descript constaint.

    The callable which is passed during instantiation is executed prior
    to  calling an Intent. The callable's return value will be evaluated
    as a bool, where True means the Intent is allowed to run, and false
    or Exception denotes an Intent's inability to run.

    More complex logic is support via subclassing Check. The logic which
    determines Intent viability must then live under a magic method
    __check__.
    """
    def __init__(self, func: Callable=None, name: str=None):
        func = getattr(self, '__check__', func)

        if func is None:
            raise TypeError(
                'advanced checks must either supply positional argument `func` '
                'or define method __check__'
            )

        super().__init__(func)
        self.name = name

    def __call__(self, ctx: Context, *a, **kw) -> bool:
        return super().__call__(ctx, *a, loop=ctx.hauto.loop, **kw)

    def __str__(self):
        try:
            self.__check__
            f = '__check__'
        except AttributeError:
            f = self.func.__name__.strip('<').strip('>')

        n = '' if self.name is None else f' "{self.name}"'
        return f'<Check{n} {f}>'

    def __repr__(self):
        if hasattr(self, '__check__'):
            f = '__check__'
        else:
            f = self.func

        s = f'<Check func={f}'

        if self.name is not None:
            s += f', name="{self.name}"'

        return f'{s}>'


class Cooldown(Check):
    """
    A special check which limits successive Intent execution.
    """
    def __init__(self, *a, **kw):
        if type(self) is Cooldown:
            raise HautoException(
                'the Cooldown class does nothing on its own, try using one of '
                'the Throttle or Debounce classes instead!'
            )

        super().__init__()


# Information on Debounce and Throttle
#
# Further Reading:
#   https://css-tricks.com/debouncing-throttling-explained-examples/


class Debounce(Cooldown):
    """
    Disallow successive fires during the wait period.

    Debouncing Intent calls allows us to group successive calls together. When
    we trail debounce, calls to an Intent that do not <wait> the appropriate
    amount of time will fail the check. This is useful when a noisy event's
    last fire is important. When we lead debounce, the first call to an Intent
    will pass, but successive calls that occur within the <wait> period will
    fail. This can be especially useful in "muting" a noisy event for a period
    of time.

    Attributes
    ----------
    wait : float
        amount of time in seconds to debounce

    edge : str = 'TRAILING'
        either LEADING or TRAILING
    """
    def __init__(self, wait: float, *, edge: str='TRAILING'):
        if edge.upper() not in ('LEADING', 'TRAILING'):
            raise ValueError(f'edge must be one of "LEADING" or "TRAILING", got {edge}')

        super().__init__()
        self.wait = wait
        self.edge = edge.upper()
        self.last_seen = None

    def __check_leading__(self, now: pendulum.DateTime):
        try:
            elapsed = (now - self.last_seen).total_seconds()
        except TypeError:
            pass
        else:
            if elapsed < self.wait:
                return False

        return True

    async def __check_trailing__(self):
        this_task = asyncio.current_task()

        try:
            self._trailing_waiter.cancel()
        except AttributeError:
            self._trailing_waiter = this_task

        try:
            await asyncio.sleep(self.wait)
        except asyncio.CancelledError:
            return False

        return True

    async def __check__(self, ctx: Context, *a, **kw) -> bool:
        if self.edge == 'LEADING':
            r = self.__check_leading__(ctx.when)

        if self.edge == 'TRAILING':
            r = await self.__check_trailing__()

        self.last_seen = ctx.when
        return r

    def __str__(self):
        e = 'immediate' if self.edge == 'LEADING' else 'lagging'
        w = self.wait
        return f'<Debounce {e}, wait={w}s>'

    def __repr__(self):
        w = self.wait
        e = self.edge
        return f'Debounce({w}, edge={e})'


class Throttle(Cooldown):
    """
    Disallow fires by a number of tokens every delta seconds.

    The main difference between Throttle and Debounce is that Throttle
    guarantees the execution of an Intent regularly, at least <token>
    times every <seconds>.

    Attributes
    ----------
    seconds : float = 1.0
        number of seconds between period resets

    tokens : int = 1.0
        number of allowable requests within a period
    """
    def __init__(self, seconds: int=1.0, *, max_tokens: float=1.0):
        super().__init__()
        self._seconds = seconds
        self._max_tokens = max_tokens
        self.tokens = max_tokens
        self.last_seen = None

    @property
    def retry_after(self) -> int:
        """
        Return the number of seconds until next token.
        """
        return max(0, 1 - self.tokens) * self._seconds

    def _adjust_capacity(self, now: pendulum.DateTime) -> None:
        """
        Eagerly set the capacity for this Cooldown.
        """
        if self.last_seen is None or (self.tokens == self._max_tokens):
            self.last_seen = now
            return

        elapsed = (now - self.last_seen).total_seconds()
        new_tokens = elapsed / self._seconds
        self.tokens = min(self.tokens + new_tokens, self._max_tokens)
        self.last_seen = now

    @safe_sync
    def __check__(self, ctx: Context, *a, **kw) -> bool:
        self._adjust_capacity(ctx.when)

        if self.tokens < 1:
            return False

        self.tokens -= 1
        return True

    def __str__(self):
        r = self._max_tokens / self._seconds
        a = self.retry_after
        return f'<Throttle [{r :.2f} tok/s], next token in {a}s>'

    def __repr__(self):
        s = self._seconds
        t = self._max_tokens
        return f'Throttle({s}, max_tokens={t})'


def check(predicate: [Callable, Check], *, name: str=None) -> Check:
    """
    Add a constraint to an Intent.

    This method is used as a decorator.

    Parameters
    ----------
    predicate : Callable
        constraint to test

    name : str = None
        name of the resulting Check
    """
    if isinstance(predicate, Check):
        _check = predicate
    else:
        _check = Check(predicate, name=name)

    def _wrapper(fn):
        try:
            fn.__checks__.append(_check)
        except AttributeError:
            fn.__checks__ = [_check]

        return fn

    return _wrapper


def debounce(*, wait: float, edge: str='TRAILING') -> Debounce:
    """
    Add a Debounce to an Intent.

    This method is used as a decorator.

    Parameters
    ----------
    wait : float
        amount of time in seconds to debounce

    edge : str = 'TRAILING'
        either LEADING or TRAILING
    """
    return check(Debounce(wait, edge=edge))


def throttle(*, tokens: int=1, seconds: float=1.0) -> Throttle:
    """
    Add a Throttler to an Intent.

    This method is used as a decorator.

    Parameters
    ----------
    tokens : int = 1
        number of allowable requests within a period

    seconds : float = 1.0
        number of seconds between period resets
    """
    return check(Throttle(seconds, max_tokens=tokens))
