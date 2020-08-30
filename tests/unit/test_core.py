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

    _, intents = await hauto.bus.fire('DUMMY', parent='ward')
    assert len(intents) == 5

    _, intents = await hauto.bus.fire('NULL', parent='ward')
    assert len(intents) == 0


@test('EventBus waits for Intents to complete', tags=['unit'])
async def _(cfg=cfg_hauto):
    hauto = HAutomate(cfg)
    i = 0

    async def _dummy(ctx):
        """
        IO time is spaced out in 0.05s intervals.

        This should ensure that only 1 intent resolves in a single event
        loop cycle, even on slower machines. This helps to test
        FIRST_COMPLETED. We're really just looking to ensure
        reproducibility here.
        """
        nonlocal i
        i += 1
        await asyncio.sleep(i * 0.01)

    for _ in range(5):
        hauto.bus.subscribe('DUMMY', _dummy)

    done, todo = await hauto.bus.fire('DUMMY', parent='ward')
    assert len(done) == 0
    assert len(todo) == 5

    done, todo = await hauto.bus.fire('DUMMY', parent='ward', wait='FIRST_COMPLETED')
    assert len(done) == 1
    assert len(todo) == 4

    done, todo = await hauto.bus.fire('DUMMY', parent='ward', wait='ALL_COMPLETED')
    assert len(done) == 5
    assert len(todo) == 0

    done, todo = await hauto.bus.fire('NULL', parent='ward')
    assert len(done) == 0
    assert len(todo) == 0


@test('Core processes many events', tags=['unit'])
async def _(cfg=cfg_hauto):
    hauto = HAutomate(cfg)
    intent_1 = hauto.bus.subscribe('DUMMY', intent=lambda *a, ctx, **kw: 1)
    intent_2 = hauto.bus.subscribe('DUMMY', intent=lambda *a, ctx, **kw: 2)
    intent_3 = hauto.bus.subscribe('DUMMY', intent=lambda *a, ctx, **kw: 3)

    assert intent_1.calls == 0
    assert intent_2.calls == 0
    assert intent_3.calls == 0

    await hauto.bus.fire('DUMMY', parent='ward')
    hauto.loop.call_soon(asyncio.create_task, hauto.stop())
    await hauto.start()

    assert intent_1.calls == 1
    assert intent_2.calls == 1
    assert intent_3.calls == 1
