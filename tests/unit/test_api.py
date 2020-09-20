import asyncio
import random
import time

from ward import test, each, raises
import pendulum

from hautomate.apis.moment.settings import Config as MomentConfig
from hautomate.apis.moment.events import EVT_TIME_SLIPPAGE
from hautomate.util.async_ import safe_sync
from hautomate.context import Context
from hautomate.errors import HautoError
from hautomate.intent import Intent
from hautomate.api import API, api_method
from hautomate.app import App
from hautomate import HAutomate

from tests.fixtures import cfg_hauto


class DummyApi(API, name='dummy_api'):
    """ Just a dummy. """

    @api_method
    def foo(self, evt='DUMMY', *, fn=None, value=0):
        return Intent(evt, fn)


@test('fn decorated with @api_method can be called as a decorator', tags=['unit'])
def _(cfg=cfg_hauto):
    cfg.api_configs = {
        'dummy_api': None
    }

    hauto = HAutomate(cfg)
    hauto.apis._load_all_apis(None)

    # apps are loaded after APIs are, in all cases .. so we simulate that here

    class Hello(App):
        """ """
        @DummyApi.foo()
        def world(self, ctx):
            nonlocal counter
            counter += 1

    # simulate registering the app

    app = Hello(hauto)
    hauto.apps._register('hello', app)

    counter = 0
    ctx_data = {
        'event_data': {},
        'when': pendulum.now(),
        'parent': 'ward.test'
    }

    # run the intent a random number of times
    x = random.randint(0, 5)

    for intent in hauto.bus._events['DUMMY']:
        ctx = Context(hauto, 'DUMMY', target=intent, **ctx_data)

        for _ in range(x):
            hauto.loop.run_until_complete(intent(ctx))

    assert isinstance(Hello.world, Intent) is False
    assert isinstance(app.world, Intent) is False
    assert counter == x


@test('fn decorated with @api_method can be called inline with explicit kw=method', tags=['unit'])
def _(cfg=cfg_hauto):
    cfg.api_configs = {
        'dummy_api': None
    }

    hauto = HAutomate(cfg)
    hauto.apis._load_all_apis(None)

    @DummyApi.foo('DUMMY')
    def hello_world(ctx):
        """ """
        nonlocal counter
        counter += 1

    counter = 0
    ctx_data = {
        'event_data': {},
        'when': pendulum.now(),
        'parent': 'ward.test'
    }

    intent = DummyApi.foo('DUMMY', fn=hello_world)

    # run the intent a random number of times
    x = random.randint(0, 5)

    for intent in hauto.bus._events['DUMMY']:
        ctx = Context(hauto, 'DUMMY', target=intent, **ctx_data)

        for _ in range(x):
            hauto.loop.run_until_complete(intent(ctx))

    assert isinstance(hello_world, Intent) is False
    assert isinstance(intent, Intent) is True
    assert counter == x

    # test the bad-user scenario, note the lack of fn keyword argument
    with raises(TypeError):
        _intent = DummyApi.foo('DUMMY', hello_world, value=0)
        _intent()

    with raises(TypeError):
        _intent = DummyApi.foo(hello_world)
        _intent()


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
