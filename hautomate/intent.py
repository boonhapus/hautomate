import itertools as it
import asyncio

import async_timeout
import pendulum


_intent_id = it.count()


class NoIntentsReady(StopAsyncIteration):
    pass


class IntentQueue(asyncio.PriorityQueue):

    def __init__(self):
        super().__init__(maxsize=-1)

    async def collect(self, timeout=1):
        """
        """
        now = pendulum.now(tz='UTC').timestamp()
        intents = []

        while True:
            try:
                async with async_timeout.timeout(timeout):
                    intent = await self.get()
            except asyncio.TimeoutError:
                break

            if intent.timestamp > now:
                self.put_nowait(intent)
                break

            intents.append(intent)

        return intents

    def __aiter__(self):
        return self

    async def __anext__(self):
        intents = await self.collect()

        if not intents and self.empty():
            raise NoIntentsReady

        return intents


class Intent:

    def __init__(self, event, func, *, timestamp=0):
        self._id = next(_intent_id)
        self.event = event
        self.func = func
        self.timestamp = timestamp

    def __lt__(self, other):
        return (self.timestamp, self._id) < (other.timestamp, other._id)

    def __repr__(self):
        event = self.event
        func = self.func
        timestamp = self.timestamp
        return f'<Intent({event=}, {func=}, {timestamp=}>'
