import collections
import asyncio

from hautomate.context import Context
from hautomate.events import EVT_ANY
from hautomate.api import API


class Trigger(API):
    """

    """
    def __init__(self, hauto):
        super().__init__(hauto)
        self._event_waiters = collections.defaultdict(lambda: asyncio.Event())

    #

    async def on_start(self, ctx: Context, *args, **kwargs):
        """
        Called once HAutomate is ready to begin processing events.
        """
        # self.on(EVT_ANY, method=self.on_almost_any_event)
        from hautomate.intent import Intent
        from hautomate.events import (
            _EVT_INIT, EVT_APP_LOAD, EVT_APP_UNLOAD,
            EVT_INTENT_SUBSCRIBE, EVT_INTENT_START, EVT_INTENT_END
        )
        from hautomate.check import Check

        _META_EVENTS = (
            _EVT_INIT, EVT_APP_LOAD, EVT_APP_UNLOAD,
            EVT_INTENT_SUBSCRIBE, EVT_INTENT_START, EVT_INTENT_END
        )

        check = Check(lambda ctx: ctx.event not in _META_EVENTS)
        intent = Intent(EVT_ANY, self.on_almost_any_event, checks=[check])
        self.hauto.bus.subscribe(EVT_ANY, intent)

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

    async def wait_for(self, event_name: str):
        """
        Block until the next time <event_name> is seen.

        This method can be used to await any incoming event except TIME_UPDATE.
        It is particularly handy when waiting for an outside (of HAutomate)
        event to be pushed into the platform.
        """
        evt = event_name.upper()

        # TODO
        #   optionally, we can extend this with a timeout param & asyncio.wait_for()
        #
        # evt = self._event_waiters[event_name]
        # await asyncio.wait_for(evt.wait(), timeout)
        await self._event_waiters[evt].wait()
