from typing import Union
from asyncio import AbstractEventLoop
import collections
import asyncio
import logging

import pendulum

from .settings import HautoConfig
from .context import Context
from .intent import Intent
from .events import _EVT_INIT, EVT_START, EVT_READY, EVT_CLOSE
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
        self._stopped = asyncio.Event(loop=self.loop)
        self._state = CoreState.initialized

    @property
    def is_running(self) -> bool:
        """
        Determine whether or not HAutomate is running.
        """
        return self._state not in (CoreState.stopped, CoreState.finished)

    @property
    def now(self) -> pendulum.DateTime:
        """
        Get HAutomate's current time.
        """
        return 'now'  # TODO

    #

    async def _intent_runner(self, ctx: Context, intent: Intent):
        """
        Wrapper around Intent execution.

        Intent Runner catches errors during execution and handles them
        gracefully.
        """
        if not await intent.can_run(ctx):
            return

        # await self.bus.fire(EVT_INTENT_START)

        try:
            await intent(ctx)
        except asyncio.CancelledError:
            _log.error(f'intent {intent} cancelled!')
        except Exception:
            _log.exception(f'intent {intent} errored!')
            # if hasattr(intent.parent, 'on_intent_error'):
            #     await intent.parent.on_intent_error(ctx, error=exc)
        # finally:
        #     await self.bus.fire(EVT_INTENT_END)

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
        self._state = CoreState.starting

        # We're doing I/O here .. but hey, who cares? No one's listening yet! :)
        # self._load_apis()
        # self.apps._initial_load_apps()
        self.loop.set_debug(debug)

        # shh, this event is super secret!
        await self.bus.fire(_EVT_INIT, parent=self, wait='ALL_COMPLETED')
        await self.bus.fire(EVT_START, parent=self, wait='ALL_COMPLETED')
        self._state = CoreState.ready
        await self.bus.fire(EVT_READY, parent=self, wait='ALL_COMPLETED')
        await self._stopped.wait()

    async def stop(self):
        """
        Stop Hautomate.
        """
        self._state = CoreState.closing
        await self.bus.fire(EVT_CLOSE, parent=self)
        self._state = CoreState.stopped
        self._stopped.set()


class EventBus:
    """
    A registry of events and their associated Intents.

    The EventBus is responsible for communicating events throughout the
    Hautomate platform. Events are consumed in a pub-sub architecture.
    """
    def __init__(self, hauto: 'HAutomate'):
        self.hauto = hauto
        self._events = collections.defaultdict(list)

    def subscribe(self, event: str, intent: Intent):
        """
        Add an Intent to the registry.
        """
        if not isinstance(intent, Intent):
            intent = Intent(event, intent)

        self._events[intent.event].append(intent)
        return intent

    async def fire(self, event: str, *, parent: Union[Intent, HAutomate], wait: str=None):
        """
        Fire an event at the registry.

        Parameters
        ----------
        event : str
            name of trigger event

        parent : Intent or HAutomate
            source of the event trigger

        wait : str
            one of FIRST_COMPLETED, ALL_COMPLETED, FIRST_EXCEPTION

        Returns
        -------
        done, pending : set[Intents, ...]
        """
        intents = set()

        if event in self._events:
            intents.update(self._events[event])

        ctx_data = {
            'hauto': self.hauto,
            'event': event,
            # 'target': <filled below>,
            'parent': parent if parent is not None else self.hauto,
        }

        tasks = []

        for intent in intents:
            ctx = Context(**ctx_data, target=intent)
            wrapped = self.hauto._intent_runner(ctx, intent)
            task = asyncio.create_task(wrapped)
            tasks.append(task)

        if tasks and (wait is not None):
            done, pending = await asyncio.wait(tasks, return_when=wait)
        else:
            done = set()
            pending = intents

        return done, pending
