from ward import test, each, raises, fixture

import pendulum

from hautomate.context import Context
from hautomate.check import Check, Cooldown
from hautomate import HAutomate

from tests.fixtures import cfg_hauto


_CONSTRAINTS = (
    Check(lambda ctx: ctx.event is None),
    Check(lambda ctx: ctx.event is not None),
    Check(lambda ctx: 1 / 0),
    Check(lambda ctx: ctx.event)
)


_CLASSIFY = (
    True,
    False,
    'raise',
    'raise'
)


@test('Check returns only True or False', tags=['async', 'unit'])
async def _(cfg=cfg_hauto, check=each(*_CONSTRAINTS[:2])):
    hauto = HAutomate(cfg)
    ctx = Context(hauto, None, target='Intent', parent='ward.test', when=pendulum.now(tz='UTC'))
    r = await check(ctx)
    assert r is True or r is False
