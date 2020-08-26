import asyncio

from ward import test, skip

from hautomate.intent import Intent
from hautomate.enums import CoreState
from hautomate import HAutomate

from tests.fixtures import cfg_hauto


@test('HAutomate.start, .stop', tags=['integration', 'async'])
async def _(cfg=cfg_hauto):
    hauto = HAutomate(cfg)
    assert hauto._state == CoreState.initialized

    # start up in the background
    asyncio.create_task(hauto.start())

    # do some processing
    hauto.bus.subscribe('DUMMY', lambda *a, **kw: None)
    await hauto.bus.fire('DUMMY')

    await hauto.stop()
    assert hauto._state == CoreState.stopped
    assert hauto._stopped.is_set() is True
    assert hauto.is_running is False


@skip('TBD: how to get this running without killing the event loop!')
@test('HAutomate.run', tags=['integration', 'async'])
def _(cfg=cfg_hauto):
    hauto = HAutomate(cfg)

    asyncio.run_coroutine_threadsafe(hauto.stop(), hauto.loop)
    hauto.run()
    assert hauto._state == CoreState.stopped
    assert hauto._stopped.is_set() is True
    assert hauto.is_running is False


@test('EventBus adds all callables as Intents', tags=['unit'])
def _(cfg=cfg_hauto):
    hauto = HAutomate(cfg)
    assert len(hauto.bus._events) == 0

    # with a naked callable
    intent = lambda *a, **kw: None
    hauto.bus.subscribe('DUMMY', intent)
    assert len(hauto.bus._events) == 1
    assert len(hauto.bus._events['DUMMY']) == 1

    # with an Intent
    intent = Intent('DUMMY', lambda *a, **kw: None)
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
        hauto.bus.subscribe('DUMMY', lambda *a, **kw: None)

    intents = await hauto.bus.fire('DUMMY')
    assert len(intents) == 5

    intents = await hauto.bus.fire('NULL')
    assert len(intents) == 0
