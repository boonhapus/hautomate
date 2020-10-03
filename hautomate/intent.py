from typing import Callable
import itertools as it
import warnings
import asyncio

from hautomate.util.async_ import Asyncable
from hautomate.context import Context
from hautomate.enums import IntentState
from hautomate.check import Cooldown
from hautomate.app import App


_intent_id = it.count()


class Intent(Asyncable):
    """
    Represents a work item to be done.

    Intents are the core building block of Hautomate. They are callable
    items similar to asyncio's Task, in that they hold an internal state
    and represent work that will be done in the future.
    """
    def __init__(self, event: str, fn: Callable, *, checks: list=None, limit: int=-1):
        super().__init__(fn)

        try:
            existing_checks = fn.__checks__
        except AttributeError:
            existing_checks = []
        finally:
            all_checks = [*existing_checks, *(checks or [])]
            checks = [c for c in all_checks if not isinstance(c, Cooldown)]
            cooldown = next((c for c in all_checks if isinstance(c, Cooldown)), None)

        self._id = next(_intent_id)
        self.event = event.upper()
        self.checks = checks
        self.cooldown = cooldown
        self.limit = limit
        self._app = None
        self._state = IntentState.initialized

        # internal statistics
        self.runs = 0
        self.last_ran = None

        # binding to an app
        if hasattr(self.func, '__self__') and isinstance(self.func.__self__, App):
            self._bind(self.func)

    def _bind(self, method: Callable) -> None:
        """
        Replace a class's function with a bound method.
        """
        self.func = method
        self._app = method.__self__
        self._app.intents.append(self)
        self._state = IntentState.ready

    def cancel(self):
        """
        Permanently cancel the Intent.

        A cancelled Intent will not fire.
        """
        self._state = IntentState.cancelled

    def pause(self):
        """
        Set the Intent to paused.

        A paused Intent will not fire.
        """
        if self._state == IntentState.cancelled:
            warnings.warn('intent is cancelled and cannot be paused!', RuntimeWarning)
            return

        self._state = IntentState.paused

    def unpause(self):
        """
        Set the Intent to ready.
        """
        if self._state == IntentState.cancelled:
            warnings.warn('intent is cancelled and cannot be unpaused!', RuntimeWarning)
            return

        self._state = IntentState.ready

    async def can_run(self, ctx: Context, *a, **kw) -> bool:
        """
        Determine if the intent can run.
        """
        if self._state in (IntentState.paused, IntentState.cancelled):
            return False

        if self.runs >= self.limit > 0:
            return False

        if not await self._all_checks_pass(ctx):
            return False

        return True

    async def _all_checks_pass(self, ctx: Context) -> bool:
        """
        Determine if this Intent passes its checks.

        The list of checks is scheduled concurrently, but evaluated
        eagerly. This allows the Intent to fail fast in case of a long
        line of checks. Only once all checks have passed, the cooldown
        is evaluated - which keeps the cooldown from being evaluated if
        the Intent isn't meant to run in the first place.
        """
        for coro in asyncio.as_completed([chk(ctx) for chk in self.checks]):
            if not await coro:
                return False

        if self.cooldown is not None and not await self.cooldown(ctx):
            return False

        return True

    async def __runner__(self, ctx: Context, *a, **kw):
        """
        Akin to __call__, but used in an async context and tracks
        statistics on the Intent itself.
        """
        self.runs += 1

        # break race condition where more than 1 copy of an Intent can
        # qualify all check during the same iteration of the event loop,
        # but only one should actually run.
        if self.runs > self.limit > 0:
            return

        r = await super().__call__(ctx, *a, loop=ctx.hauto.loop, **kw)
        self.last_ran = ctx.hauto.now
        return r

    __call__ = __runner__
