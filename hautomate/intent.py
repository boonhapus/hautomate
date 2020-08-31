from typing import Callable
import itertools as it

from hautomate.util.async_ import Asyncable
from hautomate.context import Context


_intent_id = it.count()


class Intent(Asyncable):
    """
    Represents a work item to be done.

    Intents are the core building block of Hautomate. They are callable
    items similar to asyncio's Task, in that they hold an internal state
    and represent work that will be done in the future.
    """
    def __init__(self, event: str, func: Callable, *, limit: int=-1):
        super().__init__(func)
        self._id = next(_intent_id)
        self.event = event
        self.limit = limit

        # internal statistics
        self.runs = 0
        self.last_ran = None

    async def can_run(self, ctx: Context, *a, **kw) -> bool:
        """
        Determine if the intent can run.
        """
        if self.runs >= self.limit > 0:
            return False

        # if self.checks is None:
        #     return True

        # if not await self._run_all_checks(ctx, *a, **kw):
        #     return False

        return True

    async def __runner__(self, ctx: Context, *a, **kw):
        self.runs += 1
        self.last_ran = ctx.hauto.now
        r = await super().__call__(ctx, *a, loop=ctx.hauto.loop, **kw)
        return r

    __call__ = __runner__

    def __repr__(self) -> str:
        e = self.event
        f = self.func
        return f'<Intent(event="{e}", func={f}>'
