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
