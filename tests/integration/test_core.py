import asyncio

from ward import test

from hautomate import HAutomate
from hautomate.enums import CoreState

from tests.fixtures import cfg_hauto


@test('HAutomate', tags=['integration', 'async'])
async def _(cfg=cfg_hauto):
    hauto = HAutomate(cfg)
    assert hauto.state == CoreState.initialized

    # start up in the background
    asyncio.create_task(hauto.start())
    assert hauto._stopped.is_set() is False
    assert hauto.is_running is True

    # do some processing
    hauto.bus.subscribe('DUMMY', lambda *a, **kw: print('text'))
    await hauto.bus.fire('DUMMY')

    await hauto.stop()
    assert hauto.state == CoreState.stopped
    assert hauto._stopped.is_set() is True
    assert hauto.is_running is False
