from typing import Callable
import itertools as it
import asyncio

from hautomate.util.async_ import Asyncable
from hautomate.context import Context
from hautomate.enums import IntentState
from hautomate.check import Cooldown


_intent_id = it.count()


class Intent(Asyncable):
    """
    Represents a work item to be done.

    Intents are the core building block of Hautomate. They are callable
    items similar to asyncio's Task, in that they hold an internal state
    and represent work that will be done in the future.
    """
    def __init__(self, event: str, func: Callable, *, checks: list=None, limit: int=-1):
        super().__init__(func)

        try:
            existing_checks = func.__checks__
        except AttributeError:
            existing_checks = []
        finally:
            all_checks = [*existing_checks, *(checks or [])]
            checks = [c for c in all_checks if not isinstance(c, Cooldown)]
            cooldown = next((c for c in all_checks if isinstance(c, Cooldown)), None)

        self._id = next(_intent_id)
        self.event = event
        self.checks = checks
        self.cooldown = cooldown
        self.limit = limit
        self._app = None
        self._state = IntentState.initialized

        # internal statistics
        self.runs = 0
        self.last_ran = None

        # binding to an app
        if hasattr(self.func, '__self__'):
            self._bind(self.func)

    def _bind(self, method: Callable) -> None:
        """
        Replace a class's function with a bound method.
        """
        self.func = method
        self._app = method.__self__
        self._app._intents.append(self)

    async def can_run(self, ctx: Context, *a, **kw) -> bool:
        """
        Determine if the intent can run.
        """
        if self.runs >= self.limit > 0:
            return False

        if self._state == IntentState.cancelled:
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
        self.last_ran = ctx.hauto.now
        return await super().__call__(ctx, *a, loop=ctx.hauto.loop, **kw)

    __call__ = __runner__

    def __repr__(self) -> str:
        e = self.event
        f = self.func
        return f'<Intent(event="{e}", func={f}>'
