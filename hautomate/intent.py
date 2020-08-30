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
    def __init__(self, event: str, func: Callable):
        super().__init__(func)
        self._id = next(_intent_id)
        self.event = event

        # internal statistics
        self.calls = 0

    def __call__(self, *args, ctx: Context, **kwargs):
        self.calls += 1
        r = super().__call__(*args, ctx=ctx, **kwargs)
        return r

    def __repr__(self) -> str:
        e = self.event
        f = self.func
        return f'<Intent(event="{e}", func={f}>'
