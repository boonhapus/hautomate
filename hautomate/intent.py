from typing import Callable, List
import itertools as it
import asyncio

import async_timeout
import pendulum

from hautomate.util.async_ import Asyncable


_intent_id = it.count()


class Intent(Asyncable):
    """
    Represents a work item to be done.

    Intents are the core building block of Hautomate. They are callable
    items similar to asyncio's Task, in that they hold an internal state
    and represent work that will be done in the future.
    """
    def __init__(self, event: str, func: Callable, *, timestamp: int=0):
        super().__init__(func)
        self._id = next(_intent_id)
        self.event = event
        self.timestamp = timestamp

    def __lt__(self, other) -> bool:
        return (self.timestamp, self._id) < (other.timestamp, other._id)

    def __repr__(self) -> str:
        e = self.event
        f = self.func
        t = self.timestamp
        return f'<Intent(event={e}, func={f}, timestamp={t}>'


class IntentQueue(asyncio.PriorityQueue):
    """
    Wrapper around the PriorityQueue that is aware of Intents.

    The IntentQueue has a few methods over the PQ that allow organized
    collection of intents. Since Intents can be triggered or scheduled
    to run in the future, grabbing many intents on one pass of the queue
    is a totally valid operation.
    """
    def __init__(self):
        super().__init__(maxsize=-1)

    async def collect(self) -> List[Intent]:
        """
        Grab all Intents which are ready at the time of call.

        Parameters
        ----------
        timeout: float = 1
          number of seconds to wait before moving on

        Returns
        -------
        List[Intent]
        """
        now = pendulum.now(tz='UTC').timestamp()
        intents = []

        while True:
            intent = await self.get()

            if intent.timestamp > now:
                self.put_nowait(intent)
                break

            intents.append(intent)

        return intents

    def __aiter__(self):
        return self

    async def __anext__(self):
        return await self.collect()
