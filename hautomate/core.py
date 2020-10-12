from typing import Union
from asyncio import AbstractEventLoop
import collections
import asyncio
import logging

import pendulum

from hautomate.settings import HautoConfig
from hautomate.context import Context
from hautomate.intent import Intent
from hautomate.events import (
    _META_EVENTS, _EVT_INIT, EVT_START, EVT_READY, EVT_STOP, EVT_CLOSE,
    EVT_INTENT_SUBSCRIBE, EVT_INTENT_START, EVT_INTENT_END,
    EVT_ANY
)
from hautomate.enums import CoreState
from hautomate.api import APIRegistry
from hautomate.app import AppRegistry


_log = logging.getLogger(__name__)


class Hautomate:
    """
    Core orchestrator for the automation environment.
    """
    def __init__(self, config: HautoConfig, *, loop: AbstractEventLoop=None):
        self._state = CoreState.initializing
        self.loop = loop or asyncio.get_event_loop()
        self.config = config
        self.bus = EventBus(self)
        self.apis = APIRegistry(self)
        self.apps = AppRegistry(self)
        self._stopped = asyncio.Event(loop=self.loop)
        self._state = CoreState.initialized

    @property
    def is_ready(self):
        """
        Determine whether or not Hautomate is ready.
        """
        return self._state == CoreState.ready

    @property
    def is_running(self) -> bool:
        """
        Determine whether or not Hautomate is running.
        """
        return self._state not in (CoreState.stopped, CoreState.finished)

    @property
    def now(self) -> pendulum.DateTime:
        """
        Get Hautomate's current time.
        """
        if not self.is_ready:
            return pendulum.now(self.config.timezone)

        return self.apis.moment.now()

    #

    async def _intent_runner(self, ctx: Context, intent: Intent):
        """
        Wrapper around Intent execution.

        Intent Runner catches errors during execution and handles them
        gracefully.
        """
        if not await intent.can_run(ctx):
            return

        # don't fire meta events during startup/shutdown
        if ctx.event not in _META_EVENTS and self.is_ready:
            await self.bus.fire(EVT_INTENT_START, parent=self, wait='ALL_COMPLETED', started_intent=intent)

        try:
            await intent(ctx)
        except asyncio.CancelledError:
            _log.error(f'intent {intent} cancelled!')
        except Exception:
            _log.exception(f'intent {intent} errored!')
            # if hasattr(intent.parent, 'on_intent_error'):
            #     await intent.parent.on_intent_error(ctx, error=exc)
        finally:

            # don't fire meta events during startup/shutdown
            if ctx.event not in _META_EVENTS and self.is_ready:
                await self.bus.fire(EVT_INTENT_END, parent=self, wait='ALL_COMPLETED', ended_intent=intent)

    #

    def run(self, debug: bool=False):
        """
        Handle starting & proper cleanup of the event loop.
        """
        try:
            self.loop.create_task(self.start())
            self.loop.run_until_complete(self._stopped.wait())
        finally:
            self.loop.run_until_complete(self.loop.shutdown_asyncgens())
            self.loop.close()

    async def start(self, debug: bool=False):
        """
        Start Hautomate.
        """
        self.loop.set_debug(debug)
        await self.bus.fire(_EVT_INIT, parent=self, wait='ALL_COMPLETED')  # APIs and internals start
        self._state = CoreState.starting
        await self.bus.fire(EVT_START, parent=self, wait='ALL_COMPLETED')  # Apps start
        self._state = CoreState.ready
        await self.bus.fire(EVT_READY, parent=self)

    async def stop(self):
        """
        Stop Hautomate.
        """
        self._state = CoreState.closing
        await self.bus.fire(EVT_CLOSE, parent=self, wait='ALL_COMPLETED')
        self._state = CoreState.stopped
        self._stopped.set()
        await self.bus.fire(EVT_STOP, parent=self, wait='ALL_COMPLETED')


class EventBus:
    """
    A registry of events and their associated Intents.

    The EventBus is responsible for communicating events throughout the
    Hautomate platform. Events are consumed in a pub-sub architecture.
    """
    def __init__(self, hauto: 'Hautomate'):
        self.hauto = hauto
        self._events = collections.defaultdict(list)

    def subscribe(self, event: str, intent: Intent):
        """
        Add an Intent to the registry.
        """
        if not isinstance(intent, Intent):
            intent = Intent(event, intent)

        self._events[intent.event].append(intent)
        coro = self.fire(EVT_INTENT_SUBSCRIBE, parent=self.hauto, created_intent=intent)

        if not self.hauto.is_ready:
            self.hauto.loop.call_soon(asyncio.create_task, coro)
        else:
            asyncio.create_task(coro)

        return intent

    async def fire(
        self,
        event: str,
        *,
        parent: Union[Intent, Hautomate],
        wait: str=None,
        **event_data
    ):
        """
        Fire an event at the registry.

        Parameters
        ----------
        event : str
            name of trigger event

        parent : Intent or Hautomate
            source of the event trigger

        wait : str
            one of FIRST_COMPLETED, ALL_COMPLETED, FIRST_EXCEPTION

        Returns
        -------
        done, pending : set[Intents, ...]
        """
        event = event.upper()
        intents = set()

        if event not in _META_EVENTS:
            intents.update(self._events[EVT_ANY])

        if event in self._events:
            intents.update(self._events[event])

        ctx_data = {
            'hauto': self.hauto,
            'event': event,
            'event_data': event_data,
            # 'target': <filled below>,
            'when': self.hauto.now,
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
