import asyncio

from ward import test, skip

from hautomate.enums import CoreState
from hautomate import HAutomate

from tests.fixtures import cfg_hauto


@test('HAutomate.start, .stop', tags=['integration', 'async'])
async def _(cfg=cfg_hauto):

    def _run_coro_soon(coro):
        asyncio.create_task(coro)

    loop = asyncio.get_event_loop()
    hauto = HAutomate(cfg)
    assert hauto._state == CoreState.initialized

    hauto.bus.subscribe('DUMMY', lambda *a, **kw: None)

    # queue up some processing
    coros = [
        hauto.start(),
        hauto.bus.fire('DUMMY_1'),
        hauto.bus.fire('DUMMY_2'),
    ]

    for coro in coros:
        loop.call_soon(_run_coro_soon, coro)

    # allow our queued tasks to begin
    await asyncio.sleep(0.01)

    # we've started HAuto now
    assert hauto._state == CoreState.ready
    assert hauto._stopped.is_set() is False
    assert hauto.is_running is True

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
