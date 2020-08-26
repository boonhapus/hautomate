from ward import test

from hautomate.intent import Intent
from hautomate import HAutomate

from tests.fixtures import cfg_hauto


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
