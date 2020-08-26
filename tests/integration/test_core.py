import asyncio

from ward import test, skip

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
