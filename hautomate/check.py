from typing import Callable

import pendulum

from hautomate.util.async_ import Asyncable, safe_sync
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


# TODO:
#
#   Possibly incorporate idea of "debounce" and "throttling" as commonly seen
#   in practice for webpages.
#
# further reading:
#   https://css-tricks.com/debouncing-throttling-explained-examples/
#


class Cooldown(Check):
    """
    A special check which limits successive Intent execution.

    Attributes
    ----------
    delta : float
        number of seconds between period resets

    tokens : int
        number of allowable requests within a period
    """
    def __init__(self, delta: float=1.0, *, max_tokens: float=1.0):
        super().__init__()
        self.delta = delta
        self.tokens = max_tokens
        self._max_tokens = max_tokens
        self.last_seen = None

    @property
    def retry_after(self) -> int:
        """
        Return the amount of seconds required until our next token.
        """
        return max(0, 1 - self.tokens) * self.delta

    def _adjust_capacity(self, now: pendulum.DateTime) -> None:
        """
        Eagerly alter the current capacity of the cooldown.
        """
        if self.last_seen is None or (self.tokens == self._max_tokens):
            self.last_seen = now
            return

        elapsed = (now - self.last_seen).total_seconds()
        new_tokens = elapsed / self.delta
        self.tokens = min(self.tokens + new_tokens, self._max_tokens)
        self.last_seen = now

    @safe_sync
    def __check__(self, ctx: Context, *args, **kwargs) -> bool:
        """
        Determine if the Intent can run.
        """
        self._adjust_capacity(ctx.when)

        if self.tokens < 1:
            return False

        self.tokens -= 1
        return True

    def __repr__(self):
        t = self._max_tokens
        s = self.delta
        return f'<Cooldown tokens={t}, seconds={s}>'


# def check(
#     predicate: Callable,
#     *,
#     name: str=None,
# ) -> Check:
#     """
#     Add a constraint to an Intent.

#     This method is used as a decorator.
#     """
#     if isinstance(predicate, Check):
#         _check = predicate
#     else:
#         _check = Check(predicate, name=name)

#     def _wrapper(fn):
#         try:
#             fn.__checks__.append(_check)
#         except AttributeError:
#             fn.__checks__ = [_check]
#         return fn

#     return _wrapper


# def cooldown(
#     *,
#     seconds: int=0,
#     minutes: int=0,
#     hours: int=0,
#     days: int=0,
#     weeks: int=0
# ) -> Cooldown:
#     """
#     Add a cooldown to an Intent.

#     This method is used as a decorator.

#     Parameters
#     ----------
#     seconds : int
#     minutes : int
#     hours : int
#     days : int
#     weeks : int
#     """
#     seconds = (
#           seconds
#         + minutes *     60
#         + hours   *   3600
#         + days    *  86400
#         + weeks   * 604800
#     )

#     if seconds == 0:
#         raise ValueError(
#             'must specify one or more of: seconds, minutes, hours, days, weeks'
#         )

#     return check(Cooldown(seconds))
