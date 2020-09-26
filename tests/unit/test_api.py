import random

from ward import test, raises

from hautomate.settings import HautoConfig
from hautomate.context import Context
from hautomate.errors import HautoError
from hautomate.intent import Intent
from hautomate.api import API, api_method
from hautomate.app import App
from hautomate import Hautomate

from tests.fixtures import cfg_data_hauto, cfg_hauto


class DummyApi(API, name='dummy_api'):
    """ Just a dummy. """

    @api_method
    def foo(self, evt='DUMMY', *, fn=None, value=0):
        """ If that was a dummy, this is a dummer. """
        return Intent(evt, fn)

    @api_method
    def bar(self, *, fn=None):
        """ Holy dummy, Batman! """
        return self.foo(fn=fn, subscribe=False)


@test('api_method declarative style aka as @decorator', tags=['unit'])
def _(cfg_data=cfg_data_hauto):
    cfg = HautoConfig(**cfg_data)

    # simulate a working api
    cfg.api_configs = {
        'dummy_api': None
    }

    hauto = Hautomate(cfg)
    hauto.apis._load_all_apis(None)

    # apps are loaded after APIs are, in all cases .. so we simulate that here

    class Hello(App):
        """ Talking about Dummys? """
        @DummyApi.foo()
        def world(self, ctx):
            """ Pretty dumb if you ask me! """
            nonlocal counter
            counter += 1

    # simulate registering the app

    app = Hello(hauto)
    hauto.apps._register('hello', app)

    counter = 0
    ctx_data = {
        'event_data': {},
        'when': hauto.now,
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


@test('declarative api_methods can call other api_methods', tags=['unit'])
def _(cfg_data=cfg_data_hauto):
    cfg = HautoConfig(**cfg_data)

    # simulate a working api
    cfg.api_configs = {
        'dummy_api': None
    }

    hauto = Hautomate(cfg)
    hauto.apis._load_all_apis(None)

    # apps are loaded after APIs are, in all cases .. so we simulate that here

    class Hello(App):
        """ Talking about Dummys? """
        @DummyApi.bar()
        def world(self, ctx):
            """ Pretty dumb if you ask me! """
            nonlocal counter
            counter += 1

    # simulate registering the app

    app = Hello(hauto)
    hauto.apps._register('hello', app)

    counter = 0
    ctx_data = {
        'event_data': {},
        'when': hauto.now,
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


@test('api_method imperative style aka with method(fn=...)', tags=['unit'])
def _(cfg_data=cfg_data_hauto):
    cfg = HautoConfig(**cfg_data)

    # simulate a working api
    cfg.api_configs = {
        'dummy_api': None
    }

    hauto = Hautomate(cfg)
    hauto.apis._load_all_apis(None)

    @DummyApi.foo('DUMMY')
    def hello_world(ctx):
        """ Probably the dumbest. """
        nonlocal counter
        counter += 1

    hauto._state = 'CoreState.starting'  # hack :~)
    counter = 0
    ctx_data = {
        'event_data': {},
        'when': hauto.now,
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
        DummyApi.foo('DUMMY', hello_world, value=0)

    with raises(TypeError):
        DummyApi.foo(hello_world)


@test('APIRegistry autosetup runs on builtin apis', tags=['unit'])
def _(cfg_data=cfg_data_hauto):
    # remove any existing api configs
    data = cfg_data.copy()
    data.pop('api_configs', None)
    cfg = HautoConfig(**data)

    hauto = Hautomate(cfg)
    hauto.apis._load_all_apis(None)
    assert hauto.apis.trigger.name == 'trigger'
    assert hauto.apis.moment.name == 'moment'

    with raises(HautoError):
        hauto.apis.some_obviously_not_included_api


@test('APIs expose .fire(), ...', tags=['unit'])
async def _(cfg=cfg_hauto):
    hauto = Hautomate(cfg)
    hauto.apis._load_all_apis(None)
    counter = 0

    async def _dummy(ctx):
        """ Dumbest of them all, eh? """
        nonlocal counter
        counter += 1

    hauto.bus.subscribe('SOME_EVENT', _dummy)
    await hauto.apis.trigger.fire('SOME_EVENT', wait='ALL_COMPLETED')
    assert counter == 1
