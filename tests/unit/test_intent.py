import ast

from ward import test, fixture
import pendulum

from hautomate.intent import IntentQueue, Intent


@fixture(scope='module')
def now():
    return pendulum.now(tz='UTC').timestamp()


@fixture(scope='module')
def dummy_intents(now=now):
    return [
        Intent('DUMMY', lambda: None, timestamp=now + 1),
        Intent('DUMMY', lambda: None),
        Intent('DUMMY', lambda: None),
        Intent('DUMMY', lambda: None),
        Intent('DUMMY', lambda: None)
    ]


# @test('IntentQueue behaves correctly', tags=['unit', 'async'])
# async def _(now: int=now):
#     queue = IntentQueue()
#     i = Intent('DUMMY', lambda *a, **kw: None, timestamp=now)
#     await queue.put(i)

#     i = Intent('DUMMY', lambda *a, **kw: None, timestamp=now + 2)
#     await queue.put(i)

#     async for intents in queue:
#         for intent in intents:
#             assert isinstance(intent, Intent)

#     intents = await queue.collect(timeout=2)
#     assert len(intents) == 0


@test('IntentQueue is AsyncIterable', tags=['unit', 'async'])
async def _(dummy_intents=dummy_intents):
    queue = IntentQueue()
    [await queue.put(i) for i in dummy_intents]

    async for intents in queue:
        assert len(intents) == 4
        break


@test('IntentQueue is ordered', tags=['unit', 'async'])
async def _(dummy_intents=dummy_intents):
    queue = IntentQueue()
    [await queue.put(i) for i in dummy_intents]
    intents = await queue.collect()
    assert intents == dummy_intents[:][1:]


@test('IntentQueue consumes ready events and moves on', tags=['unit', 'async'])
async def _(dummy_intents=dummy_intents):
    queue = IntentQueue()
    [await queue.put(i) for i in dummy_intents]

    intents = await queue.collect()
    assert len(intents) == 4

    intents = await queue.collect()
    assert len(intents) == 0


@test('IntentQueue waits for future events', tags=['unit', 'async'])
async def _(dummy_intents=dummy_intents):
    queue = IntentQueue()
    [await queue.put(i) for i in dummy_intents]

    intents = await queue.collect()
    assert len(intents) == 4

    intent = await queue.get()
    assert intent == dummy_intents[0]


@test('IntentQueue stop iteration cleanly', tags=['unit', 'async'])
async def _():
    queue = IntentQueue()

    async for intents in queue:
        pass
