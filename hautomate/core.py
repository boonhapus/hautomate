from asyncio import AbstractEventLoop
import collections
import asyncio
import logging

from .settings import HautoConfig
from .intent import IntentQueue, Intent
from .enums import CoreState


_log = logging.getLogger(__name__)


class HAutomate:
    """
    Core orchestrator for the automation environment.
    """
    def __init__(self, config: HautoConfig, *, loop: AbstractEventLoop=None):
        self.loop = loop or asyncio.get_event_loop()
        self.config = config
        self.bus = EventBus(self)
        self._intent_queue = IntentQueue()
        self._stopped = asyncio.Event(loop=self.loop)
        self._state = CoreState.initialized

    @property
    def state(self) -> CoreState:
        """
        """
        return self._state

    @property
    def is_running(self) -> bool:
        """
        """
        return self.state not in (CoreState.stopped, CoreState.finished)

    #

    async def _consume(self):
        """
        """
        while self.is_running:
            async for intents in self._intent_queue:
                # do the thing with intents
                pass

        intents = await self._intent_queue.collect()
        # TODO: need to consume intents until we get to the first STOP event.
        # TODO: need to cancel tasks after we reach the finished event.

    #

    def run(self, debug: bool=False):
        """
        Handle starting & proper cleanup of the event loop.
        """
        try:
            asyncio.set_event_loop(self.loop)
            self.loop.run_until_complete(self.start(debug))
        finally:
            try:
                asyncio.runners._cancel_all_tasks(self.loop)
                self.loop.run_until_complete(self.loop.shutdown_asyncgens())
            finally:
                asyncio.set_event_loop(None)
                self.loop.close()

    async def start(self, debug: bool=False):
        """
        Start Hautomate.

        # 1 .     CORE CONFIG
        # 2 .      API CONFIG
        # 3 .      App CONFIG
        # 4 .       EVT_START [undocumented for Apps, essentially for API use]
        # 4a.       API_READY
        # 5 .       EVT_READY
        """
        asyncio.create_task(self._consume())
        self._state = CoreState.starting

        # We're doing I/O here .. but hey, who cares? No one's listening yet! :)
        # self._load_apis()
        # self.apps._initial_load_apps()
        # self.loop.set_debug(debug)

        # shh, this event is super secret!
        # await self.bus.fire(
        #     'INITIALIZED', return_when=ReturnWhen.all_completed, parent='CORE:HAutomate'
        # )

        # await self.bus.fire(
        #     EVT_START, return_when=ReturnWhen.all_completed, parent='CORE:HAutomate'
        # )
        self._state = CoreState.ready
        # await self.bus.fire(EVT_READY, parent='CORE:HAutomate')
        await self._stopped.wait()

    async def stop(self):
        """
        Stop Hautomate.
        """
        self._state = CoreState.closing
        # await self.bus.fire(
        #     EVT_CLOSE, return_when=ReturnWhen.all_completed, parent='CORE:HAutomate'
        # )
        self._state = CoreState.stopped
        self._stopped.set()


class EventBus:

    def __init__(self, hauto: 'HAutomate'):
        self.hauto = hauto
        self._events = collections.defaultdict(list)

    def subscribe(self, event, intent):
        """
        """
        if not isinstance(intent, Intent):
            intent = Intent(event, intent)

        self._events[event].append(intent)

    async def fire(self, event):
        """
        """
        intents = collections.deque()

        if event in self._events:
            intents.extend(self._events[event])

        for intent in intents:
            self.hauto._intent_queue.put_nowait(intent)
