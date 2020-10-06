from typing import Callable, Tuple
import collections
import asyncio
import re

from hautomate.util.async_ import safe_sync
from hautomate.context import Context
from hautomate.events import _META_EVENTS, EVT_ANY
from hautomate.intent import Intent
from hautomate.check import Check
from hautomate.api import API, api_method, public_method


class Trigger(API):
    """
    API for working with messages broadcast across the event bus.
    """
    def __init__(self, hauto):
        super().__init__(hauto)
        # self._event_waiters = collections.defaultdict(lambda: asyncio.Event())
        self._event_waiters = collections.defaultdict(lambda: hauto.loop.create_future())

    # Listeners and Internal Methods

    @safe_sync
    def on_start(self, ctx: Context):
        """
        Called once Hautomate is ready to begin processing events.
        """
        check = Check(lambda ctx: ctx.event not in _META_EVENTS)
        self.on(EVT_ANY, fn=self.almost_any_event, checks=[check])

    @safe_sync
    def almost_any_event(self, ctx: Context):
        """
        Called on every non-meta event.

        This first time an event is fired, an asyncio.Event is created. The
        event grabbed is set and cleared immediately, triggering all coroutines
        who wait on the event to be awakened. The event is then cleared so that
        new waiters may block until the next event fire.
        """
        try:
            fut = self._event_waiters.pop(ctx.event)
            fut.set_result(ctx)
        except KeyError:
            pass
        # evt = self._event_waiters[ctx.event]
        # evt.set()
        # evt.clear()

    # Public Methods

    @public_method
    async def wait_for(self, event_name: str, *, timeout: float=None):
        """
        Block until the next time <event_name> is seen.

        This method can be used to await any incoming event. It is
        particularly handy when waiting for an outside (of Hautomate)
        event to be pushed into the platform.
        """
        # evt = self._event_waiters[event_name.upper()]
        # await asyncio.wait_for(evt.wait(), timeout)
        fut = self._event_waiters[event_name.upper()]
        ctx = await asyncio.wait_for(fut, timeout)
        return ctx

    # Intents

    @api_method
    def on(self, event_name: str, *, fn: Callable, **intent_kwargs) -> Intent:
        """
        Listen for a specifc event.

        Can be used as an App function decorator. If used inline, this
        method expects a keyword argument 'fn', the intended method to
        call upon meeting the criteria. All other keyword arguments are
        passed into the Intent.

        Parameters
        ----------
        event_name : str
            event to listen for

        Returns
        -------
        intent : Intent
        """
        return Intent(event_name, fn=fn, **intent_kwargs)

    @api_method
    def any(self, *event_names: Tuple[str], fn: Callable, **intent_kwargs) -> Intent:
        """
        Listen for any event in <event_names>.

        Can be used as an App function decorator. If used inline, this
        method expects a keyword argument 'fn', the intended method to
        call upon meeting the criteria. All other keyword arguments are
        passed into the Intent.

        Parameters
        ----------
        *event_names : tuple[str]
            names of events to listen for

        Returns
        -------
        intent : Intent
        """
        evts = '|'.join(map(str.upper, event_names))
        return self.re_match(evts, fn=fn, subscribe=False, **intent_kwargs)

    @api_method
    def startswith(self, part: str, *, fn: Callable, **intent_kwargs) -> Intent:
        """
        Listen to events that begin with <part>.

        Can be used as an App function decorator. If used inline, this
        method expects a keyword argument 'fn', the intended method to
        call upon meeting the criteria. All other keyword arguments are
        passed into the Intent.

        Parameters
        ----------
        part : str
            partial match of the events to listen for

        Returns
        -------
        intent : Intent
        """
        return self.re_match(fr'^{part.upper()}.*', fn=fn, **intent_kwargs)

    @api_method
    def endswith(self, part: str, *, fn: Callable, **intent_kwargs) -> Intent:
        """
        Listen to events that end with <part>.

        Can be used as an App function decorator. If used inline, this
        method expects a keyword argument 'fn', the intended method to
        call upon meeting the criteria. All other keyword arguments are
        passed into the Intent.

        Attributes
        ----------
        part : str
            partial match of the events to listen for

        Returns
        -------
        intent : Intent
        """
        return self.re_match(fr'.*{part.upper()}$', fn=fn, **intent_kwargs)

    @api_method
    def contains(self, mid: str, *, fn: Callable, **intent_kwargs) -> Intent:
        """
        Listen to events that have <mid> within.

        Can be used as an App function decorator. If used inline, this
        method expects a keyword argument 'fn', the intended method to
        call upon meeting the criteria. All other keyword arguments are
        passed into the Intent.

        Attributes
        ----------
        mid : str
            partial match of the events to listen for

        Returns
        -------
        intent : Intent
        """
        return self.re_match(fr'.*{mid.upper()}.*', fn=fn, **intent_kwargs)

    @api_method
    def re_match(
        self,
        pattern: str,
        *,
        fn: Callable,
        **intent_kwargs
    ) -> Intent:
        """
        Listen for any event which matches a regex.

        Can be used as an App function decorator. If used inline, this
        method expects a keyword argument 'fn', the intended method to
        call upon meeting the criteria. All other keyword arguments are
        passed into the Intent.

        Parameters
        ----------
        pattern : str
            regex pattern to re.fullmatch against

        Returns
        -------
        intent : Intent
        """
        try:
            intent_kwargs['checks']
        except KeyError:
            intent_kwargs['checks'] = []

        pattern = re.compile(fr'{pattern}', flags=re.IGNORECASE)
        check = Check(lambda ctx: pattern.fullmatch(ctx.event) is not None)
        intent_kwargs['checks'].append(check)
        return Intent(EVT_ANY, fn=fn, **intent_kwargs)
