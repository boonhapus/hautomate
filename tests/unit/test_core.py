import asyncio

from ward import test

from hautomate.intent import Intent
from hautomate import HAutomate

from tests.fixtures import cfg_hauto


@test('EventBus adds all callables as Intents', tags=['unit'])
def _(cfg=cfg_hauto):
    hauto = HAutomate(cfg)
    assert len(hauto.bus._events) == 0

    # with a naked callable
    intent = lambda *a, ctx, **kw: None
    hauto.bus.subscribe('DUMMY', intent)
    assert len(hauto.bus._events) == 1
    assert len(hauto.bus._events['DUMMY']) == 1

    # with an Intent
    intent = Intent('DUMMY', lambda *a, ctx, **kw: None)
    hauto.bus.subscribe('DUMMY', intent)
    assert len(hauto.bus._events) == 1
    assert len(hauto.bus._events['DUMMY']) == 2

    # assert all subscriptions are Intents
    for intent in hauto.bus._events['DUMMY']:
        assert type(intent) is Intent


@test('EventBus fires events to 0..N receivers', tags=['unit'])
async def _(cfg=cfg_hauto):
    hauto = HAutomate(cfg)
    assert len(hauto.bus._events) == 0

    for _ in range(5):
        hauto.bus.subscribe('DUMMY', lambda *a, ctx, **kw: None)

    _, intents = await hauto.bus.fire('DUMMY')
    assert len(intents) == 5

    _, intents = await hauto.bus.fire('NULL')
    assert len(intents) == 0


@test('EventBus waits for Intents to complete', tags=['unit'])
async def _(cfg=cfg_hauto):
    hauto = HAutomate(cfg)

    import random

    async def _dummy(ctx):
        """
        Attempt to make it highly unlikely that two
        intents will have the same processing time.

        This helps test FIRST_COMPLETED.
        """
        await asyncio.sleep(random.randint(0, 50000) / 100000.0)

    for _ in range(5):
        hauto.bus.subscribe('DUMMY', _dummy)

    done, pending = await hauto.bus.fire('DUMMY')
    assert len(done) == 0
    assert len(pending) == 5

    done, pending = await hauto.bus.fire('DUMMY', wait_for='FIRST_COMPLETED')
    assert len(done) == 1
    assert len(pending) == 4

    done, pending = await hauto.bus.fire('DUMMY', wait_for='ALL_COMPLETED')
    assert len(done) == 5
    assert len(pending) == 0

    done, pending = await hauto.bus.fire('NULL')
    assert len(done) == 0
    assert len(pending) == 0


@test('Core processes many events', tags=['unit'])
async def _(cfg=cfg_hauto):
    hauto = HAutomate(cfg)
    intent_1 = hauto.bus.subscribe('DUMMY', intent=lambda *a, ctx, **kw: 1)
    intent_2 = hauto.bus.subscribe('DUMMY', intent=lambda *a, ctx, **kw: 2)
    intent_3 = hauto.bus.subscribe('DUMMY', intent=lambda *a, ctx, **kw: 3)

    assert intent_1.calls == 0
    assert intent_2.calls == 0
    assert intent_3.calls == 0

    await hauto.bus.fire('DUMMY')
    hauto.loop.call_soon(asyncio.create_task, hauto.stop())
    await hauto.start()

    assert intent_1.calls == 1
    assert intent_2.calls == 1
    assert intent_3.calls == 1
