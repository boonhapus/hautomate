import asyncio
import time

from ward import test, each, raises
import pendulum

from hautomate.apis.moment.settings import Config as MomentConfig
from hautomate.apis.moment.events import EVT_TIME_SLIPPAGE
from hautomate.util.async_ import safe_sync
from hautomate.errors import HautoError
from hautomate.intent import Intent
from hautomate.api import API, api_method
from hautomate import HAutomate

from tests.fixtures import cfg_hauto


class DummyApi(API, name='dummy_api'):
    """ Just a dummy. """

    @api_method
    def foo(self, *, func=None):
        return Intent('DUMMY', func)


@test('fn decorated with @api_method can be called as a decorator', tags=['unit', 'current'])
def _(cfg=cfg_hauto):
    # overwrite any existing api configs
    cfg.api_configs = {
        'dummy_api': None
    }

    hauto = HAutomate(cfg)
    hauto.apis._load_all_apis(None)

    @DummyApi.foo()
    def _foobar(ctx):
        return 1

    @DummyApi.foo()
    def _foobar_2(ctx):
        return 1

    # print(hauto.apis.dummy_api.foo())
    print(DummyApi.foo(func=lambda ctx: None))
    print(_foobar)
    # print(DummyApi.foo())
    assert 1 == 2


# @test('fn decorated with @api_method can be called inline with explicit kw=method')
# def _(cfg=cfg_hauto):
#     assert 1 == 2


@test('APIRegistry autosetup runs on builtin apis', tags=['unit'])
def _(cfg=cfg_hauto):
    # overwrite any existing api configs
    cfg.api_configs = {}

    hauto = HAutomate(cfg)
    hauto.apis._load_all_apis(None)
    assert hauto.apis.trigger.name == 'trigger'
    assert hauto.apis.moment.name == 'moment'

    with raises(HautoError):
        hauto.apis.some_obviously_not_included_api


@test('APIs expose .fire(), ...', tags=['unit'])
async def _(cfg=cfg_hauto):
    hauto = HAutomate(cfg)
    hauto.apis._load_all_apis(None)
    counter = 0

    async def _dummy(ctx):
        nonlocal counter
        counter += 1

    hauto.bus.subscribe('SOME_EVENT', _dummy)
    await hauto.apis.trigger.fire('SOME_EVENT', wait='ALL_COMPLETED')
    assert counter == 1


@test('Trigger API exposes waiters', tags=['unit'])
async def _(cfg=cfg_hauto):
    hauto = HAutomate(cfg)
    await hauto.start()

    # queue up a event fire and then wait on it
    asyncio.create_task(hauto.bus.fire('SOME_EVENT', parent='ward.test'))
    await hauto.apis.trigger.wait_for('SOME_EVENT')


@test('Moment API notifies on event loop slippage', tags=['unit'])
async def _(cfg=cfg_hauto):
    hauto = HAutomate(cfg)

    @safe_sync
    def hanger(ctx):
        """ this is totally not safe """
        time.sleep(0.50)

    hauto.bus.subscribe('SOME_EVENT', hanger)
    await hauto.start()

    # ensure we're not lagging
    with raises(asyncio.TimeoutError):
        await hauto.apis.trigger.wait_for(EVT_TIME_SLIPPAGE, timeout=1)

    # induce the lag
    asyncio.create_task(hauto.bus.fire('SOME_EVENT', parent='ward.test'))

    try:
        await hauto.apis.trigger.wait_for(EVT_TIME_SLIPPAGE, timeout=0.75)
    except asyncio.TimeoutError:
        assert 1 == 2, 'no slippage occurred!'

    await hauto.stop()


@test('Moment API allows time travel: speed={speed}, epoch={epoch}', tags=['unit'])
async def _(
    cfg=cfg_hauto,
    speed=each(1.0, 2.0),
    epoch=each(None, pendulum.parse('1999/12/31 12:59:00'))
):
    # overwrite any existing api configs
    cfg.api_configs = {'moment': MomentConfig(speed=speed, epoch=epoch)}
    hauto = HAutomate(cfg)
    await hauto.start()

    real_beg = time.perf_counter()
    virt_beg = hauto.now
    await asyncio.sleep(0.25)
    virt_end = hauto.now
    real_end = time.perf_counter()

    real_elapsed = real_end - real_beg
    virt_elapsed = (virt_end - virt_beg).total_seconds()

    assert round(virt_elapsed / speed, 2) == round(real_elapsed, 2)
    assert hauto.apis.moment.scale_to_realtime(0.25 * speed) == 0.25
