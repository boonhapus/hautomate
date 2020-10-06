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

        This is the results-producer for those who are waiting on the
        next valid event. Users will use trigger.wait_for in order to
        listen to the next fire of a particular event. If they are the
        first listener, an asyncio.Future is created and returned. All
        successive listners get access to that same future.

        almost_any_event will attempt to pop a future off the
        defaultdict and set its result as the inbound Context. This acts
        like an asyncio.Event with a result, notifying all those who
        await it to wake up.
        """
        try:
            fut = self._event_waiters.pop(ctx.event)
            fut.set_result(ctx)
        except KeyError:
            pass

    # Public Methods

    @public_method
    async def wait_for(self, event_name: str, *, timeout: float=None) -> Context:
        """
        Block until the next time <event_name> is seen.

        This method can be used to await any incoming event. It is
        particularly handy when waiting for an outside (of Hautomate)
        event to be pushed into the platform.

        The context under which the event waited for will be returned.
        """
        fut = self._event_waiters[event_name.upper()]

        # shield the future from cancellation if we reach a timeout so we don't
        # interfere with other waiters
        ctx = await asyncio.wait_for(asyncio.shield(fut), timeout)
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
