import collections
import asyncio

from hautomate.context import Context
from hautomate.events import _META_EVENTS, EVT_ANY
from hautomate.intent import Intent
from hautomate.api import API
from hautomate.check import Check


class Trigger(API):
    """
    API for working with messages broadcast across the event bus.
    """
    def __init__(self, hauto):
        super().__init__(hauto)
        self._event_waiters = collections.defaultdict(lambda: asyncio.Event())

    #

    async def on_start(self, ctx: Context, *args, **kwargs):
        """
        Called once HAutomate is ready to begin processing events.
        """
        check = Check(lambda ctx: ctx.event not in _META_EVENTS)
        intent = Intent(EVT_ANY, self.on_almost_any_event, checks=[check])
        self.hauto.bus.subscribe(EVT_ANY, intent)
        # self.on(EVT_ANY, method=self.on_almost_any_event)

    # @check(lambda ctx: ctx.event not in _META_EVENTS)
    async def on_almost_any_event(self, ctx: Context, *args, **kwargs):
        """
        Called on every event except TIME_UPDATE.

        This first time an event is fired, an asyncio.Event is created. The
        event grabbed is set and cleared immediately, triggering all coroutines
        who wait on the event to be awakened. The event is then cleared so that
        new waiters may block until the next event fire.
        """
        evt = self._event_waiters[ctx.event]
        evt.set()
        evt.clear()

    # PUBLIC METHODS

    async def wait_for(self, event_name: str, *, timeout: float=None):
        """
        Block until the next time <event_name> is seen.

        This method can be used to await any incoming event. It is
        particularly handy when waiting for an outside (of HAutomate)
        event to be pushed into the platform.
        """
        evt = self._event_waiters[event_name.upper()]
        await asyncio.wait_for(evt.wait(), timeout)

    # Intents

    # @api_method
    # def on(self, event_name: str, *, method=None, **intent_kwargs) -> Intent:
    #     """

    #     trigger.on(some_event, method=lambda ctx: None)

    #     @trigger.on(some_event)
    #     """
    #     if method is None:
    #         pass

    #     return Intent()
