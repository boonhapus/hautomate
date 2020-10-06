import asyncio

from ward import test, each, raises

from hautomate.util.async_ import safe_sync
from hautomate.context import Context
from hautomate.intent import Intent
from hautomate.apis import trigger
from hautomate import Hautomate

from tests.fixtures import cfg_hauto


@test('Trigger API exposes asyncio.Event-like waiters which return Context', tags=['unit'])
async def _(cfg=cfg_hauto):
    hauto = Hautomate(cfg)
    await hauto.start()

    # queue up an event and then wait on it
    asyncio.create_task(hauto.bus.fire('SOME_EVENT', parent='ward.test'))
    ctx = await trigger.wait_for('SOME_EVENT')
    assert isinstance(ctx, Context) is True

    # also catch that we allow duration
    with raises(asyncio.TimeoutError):
        await trigger.wait_for('SOME_EVENT', timeout=0.5)


@test('trigger.{method_name}() returns an Intent & validates correctly', tags=['unit'])
async def _(
    cfg=cfg_hauto,
    sig=each(
        {'args': ('DUMMY',)},
        {'args': ('DUMMY', 'DUMBER', 'DUMBEST')},
        {'args': ('DUM',)},
        {'args': ('MY',)},
        {'args': ('UMM',)},
        {'args': (r'\wUMM\w',)}
    ),
    method_name=each(
        'on',
        'any',
        'startswith',
        'endswith',
        'contains',
        're_match'
    )
):
    hauto = Hautomate(cfg)
    await hauto.start()
    counter = 0

    @safe_sync
    def increment(ctx):
        nonlocal counter
        counter += 1

    method = getattr(trigger, method_name)
    a  = sig.get('args', tuple())
    kw = sig.get('kwargs', dict())
    intent = method(*a, fn=increment, **kw)
    assert isinstance(intent, Intent) is True

    # passing condition
    await hauto.bus.fire('DUMMY', wait='ALL_COMPLETED', parent='ward.test')
    assert counter == 1

    # failing condition, counter should not increase
    await hauto.bus.fire('LOL', wait='ALL_COMPLETED', parent='ward.test')
    assert counter == 1
