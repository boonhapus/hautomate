from asyncio import AbstractEventLoop
import asyncio
import logging

from .settings import HautoConfig


_log = logging.getLogger(__name__)


class HAutomate:
    """
    Core orchestrator for the automation environment.
    """
    def __init__(self, config: HautoConfig, *, loop: AbstractEventLoop=None):
        self.loop = loop or asyncio.get_event_loop()
        self.config = config
        self._stopped = asyncio.Event(loop=self.loop)

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
        # self._state = CoreState.starting

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
        # self._state = CoreState.ready
        # await self.bus.fire(EVT_READY, parent='CORE:HAutomate')
        await self._stopped.wait()

    async def stop(self):
        """
        Stop Hautomate.
        """
        # self._state = CoreState.closing
        # await self.bus.fire(
        #     EVT_CLOSE, return_when=ReturnWhen.all_completed, parent='CORE:HAutomate'
        # )
        # self._state = CoreState.stopped
        self._stopped.set()
