import asyncio
import time

from ward import test, each, raises
import pendulum

from hautomate.apis.moment.events import EVT_TIME_SLIPPAGE
from hautomate.apis.moment.checks import MomentaryCheck
from hautomate.util.async_ import safe_sync
from hautomate.settings import HautoConfig
from hautomate.context import Context
from hautomate.intent import Intent
from hautomate.apis import moment
from hautomate import Hautomate

from tests.fixtures import cfg_data_hauto, cfg_hauto


@test('Moment API scales time correctly at speed={speed}', tags=['unit'])
async def _(
    cfg_data=cfg_data_hauto,
    speed=each(1.0, 2.0),
    seconds_in_realtime=each(0.25, 0.125),
    seconds_in_virtual=each(0.25, 0.50),
):
    # overwrite any existing api configs
    data = cfg_data.copy()
    data['api_configs'] = {'moment': {'speed': speed}}
    cfg = HautoConfig(**data)

    hauto = Hautomate(cfg)
    await hauto.start()

    assert moment.scale_time(0.25, to='realtime') == seconds_in_realtime
    assert moment.scale_time(0.25, to='virtual') == seconds_in_virtual

    with raises(ValueError):
        moment.scale_time(0.25, to='invalid')


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

    hauto = Hautomate(cfg)
    await hauto.start()

    real_beg = time.perf_counter()
    virt_beg = hauto.now
    # in terms of timing, we'll sleep for at least 0.1s. asyncio makes best
    # effort suspend execution for exactly 0.1s, but due to nature of asyncio
    # it will always be over that much.. this is important for the assert stmt
    await asyncio.sleep(0.1)
    virt_end = hauto.now
    real_end = time.perf_counter()

    real_elapsed = real_end - real_beg
    virt_elapsed = (virt_end - virt_beg).total_seconds()

    assert round(virt_elapsed / speed, 1) == round(real_elapsed, 1)


@test('Moment API notifies on event loop slippage', tags=['unit'])
async def _(cfg=cfg_hauto):
    hauto = Hautomate(cfg)
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


@test('moment.{method_name} returns an Intent; {sig}', tags=['unit'])
async def _(
    cfg=cfg_hauto,
    sig=each(
        {'args': (pendulum.now().subtract(seconds=1),)},
        {'args': (-1,)},
        {'args': ('1999/12/31',)},
        {'args': ('12:34',)},
        {'args': (pendulum.duration(seconds=1),)},
        {'args': (1,)},
        {'args': ('1',), 'error': ValueError},
        {'args': (1,)},
        {'args': (pendulum.duration(seconds=1),)},
        {'args': ('1',), 'error': TypeError}
    ),
    method_name=each(
        'at',
        'at',
        'at',
        'at',
        'soon',
        'soon',
        'soon',
        'every',
        'every',
        'every'
    )
):
    hauto = Hautomate(cfg)
    await hauto.start()
    method = getattr(moment, method_name)
    a  = sig.get('args', tuple())
    kw = sig.get('kwargs', dict())
    e  = sig.get('error', None)

    if e is not None:
        with raises(e):
            intent = method(*a, fn=lambda ctx: None, **kw)
    else:
        intent = method(*a, fn=lambda ctx: None, **kw)
        assert isinstance(intent, Intent) is True


@test('MomentaryCheck', tags=['unit'])
async def _(
    cfg=cfg_hauto,
    dt_or_time=each(None, pendulum.parse('0:00:00', exact=True))
):
    hauto = Hautomate(cfg)
    await hauto.start()
    now = pendulum.now()
    chk = MomentaryCheck(dt_or_time or now)

    ctx_kw = {
        'event_data': {},
        'target': 'Intent',
        'parent': 'ward.test'
    }

    ctx = Context(hauto, 'TIME_UPDATE', when=now.subtract(years=42), **ctx_kw)
    await chk(ctx) is True

    s = hauto.apis.moment.resolution
    ctx = Context(hauto, 'TIME_UPDATE', when=now.subtract(seconds=s), **ctx_kw)
    await chk(ctx) is True

    ctx = Context(hauto, 'TIME_UPDATE', when=now, **ctx_kw)
    await chk(ctx) is True

    ctx = Context(hauto, 'TIME_UPDATE', when=now.add(years=42), **ctx_kw)
    await chk(ctx) is False
