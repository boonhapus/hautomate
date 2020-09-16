import asyncio

from ward import test

from hautomate.events import EVT_READY
from hautomate.enums import CoreState
from hautomate import HAutomate

from tests.fixtures import cfg_hauto


@test('HAutomate.start, .stop', tags=['integration'])
async def _(cfg=cfg_hauto):
    hauto = HAutomate(cfg)
    assert hauto._state == CoreState.initialized

    # simulate some intents
    hauto.bus.subscribe('DUMMY', lambda ctx: None)
    hauto.bus.subscribe('INTENT_START', lambda ctx: None)

    await hauto.start()
    assert hauto._state == CoreState.ready
    assert hauto._stopped.is_set() is False
    assert hauto.is_running is True

    await hauto.bus.fire('DUMMY', parent='ward.tests')
    asyncio.create_task(hauto.bus.fire('SOME_FOREIGN_EVENT', parent='ward.tests'))
    await hauto.apis.trigger.wait_for('SOME_FOREIGN_EVENT')

    await hauto.stop()
    assert hauto._state == CoreState.stopped
    assert hauto._stopped.is_set() is True
    assert hauto.is_running is False


@test('HAutomate.run', tags=['integration'])
def _(cfg=cfg_hauto):
    # explicitly get an event_loop so that we don't conflict with Ward
    loop = asyncio.new_event_loop()

    hauto = HAutomate(cfg, loop=loop)

    async def _pipeline(ctx):
        await hauto.apis.trigger.wait_for('SOME_FOREIGN_EVENT')
        await hauto.stop()

    coro = hauto.bus.fire('SOME_FOREIGN_EVENT', parent='ward.tests')
    hauto.loop.call_later(0.5, asyncio.create_task, coro)
    hauto.bus.subscribe(EVT_READY, _pipeline)

    assert hauto._state == CoreState.initialized

    hauto.run()

    assert hauto._state == CoreState.stopped
    assert hauto._stopped.is_set() is True
    assert hauto.is_running is False
