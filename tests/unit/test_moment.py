import asyncio
import time

from ward import test, each, raises
import pendulum

from hautomate.apis.moment.events import EVT_TIME_SLIPPAGE
from hautomate.util.async_ import safe_sync
from hautomate.settings import HautoConfig
from hautomate import HAutomate

from tests.fixtures import cfg_data_hauto, cfg_hauto


@test('Moment API allows time travel: speed={speed}, epoch={epoch}', tags=['unit'])
async def _(
    cfg_data=cfg_data_hauto,
    speed=each(1.0, 2.0),
    epoch=each(None, pendulum.parse('1999/12/31 12:59:00'))
):
    # overwrite any existing api configs
    data = cfg_data.copy()
    data['api_configs'] = {'moment': {'speed': speed, 'epoch': epoch}}
    cfg = HautoConfig(**data)

    hauto = HAutomate(cfg)
    await hauto.start()

    real_beg = time.perf_counter()
    virt_beg = hauto.now
    # in terms of timing, we'll sleep for at least 0.25s. asyncio makes best
    # effort suspend execution for exactly 0.25s, but due to nature of asyncio
    # it will always be over that much.. this is important for the assert stmt
    await asyncio.sleep(0.25)
    virt_end = hauto.now
    real_end = time.perf_counter()

    real_elapsed = real_end - real_beg
    virt_elapsed = (virt_end - virt_beg).total_seconds()

    assert round(virt_elapsed / speed, 1) == round(real_elapsed, 1)
    assert hauto.apis.moment.scale_to_realtime(0.25 * speed) == 0.25


@test('Moment API notifies on event loop slippage', tags=['unit'])
async def _(cfg=cfg_hauto):
    hauto = HAutomate(cfg)
    await hauto.start()

    @safe_sync
    def hanger(ctx):
        """ This is totally not safe """
        time.sleep(1.00)

    hauto.bus.subscribe('SOME_EVENT', hanger)

    # ensure we're not lagging
    with raises(asyncio.TimeoutError):
        await hauto.apis.trigger.wait_for(EVT_TIME_SLIPPAGE, timeout=0.5)

    # induce the lag
    asyncio.create_task(hauto.bus.fire('SOME_EVENT', parent='ward.test'))

    try:
        await hauto.apis.trigger.wait_for(EVT_TIME_SLIPPAGE, timeout=1.5)
    except asyncio.TimeoutError:
        assert 1 == 2, 'no slippage occurred!'

    await hauto.stop()
