from ward import test, each, raises, fixture

import pendulum

from hautomate.context import Context
from hautomate.errors import CheckError
from hautomate.check import Check, Cooldown
from hautomate import HAutomate

from tests.fixtures import cfg_hauto


class AdvancedCheck(Check):

    def __check__(self, ctx, *a, **kw):
        return True


class AsyncAdvancedCheck(Check):

    async def __check__(self, ctx, *a, **kw):
        return True


def raise_exc(exc):
    def _decorator(ctx):
        raise exc

    return _decorator


_TRIALS = {
    'passes': (
        *[Check(lambda ctx: r) for r in (True, False, 1, 0, 'a')],
        AdvancedCheck(),
        AsyncAdvancedCheck(),
        Cooldown()
    ),
    'good_errors': (
        Check(raise_exc(CheckError)),
    ),
    'bad_errors': (
        Check(lambda ctx: 1 / 0, name='DivByZeroCheck'),
    )
}


@fixture(scope='module')
def hauto(cfg=cfg_hauto):
    return HAutomate(cfg)


@fixture(scope='module')
def ctx(hauto=hauto):
    data = {
        'target': 'Intent',
        'parent': 'ward.test',
        'when': pendulum.now(tz='UTC')
    }
    return Context(hauto, None, **data)


@test('{check} evaluates as bool', tags=['async', 'unit'])
async def _(ctx=ctx, check=each(*_TRIALS['passes'])):
    r = await check(ctx)
    r_bool = bool(r)
    assert r_bool in (True, False)


@test('{check} can only raise CheckErrors [good errors]', tags=['async', 'unit'])
async def _(ctx=ctx, check=each(*_TRIALS['good_errors'])):
    with raises(CheckError):
        await check(ctx)


@test('{check} can only raise CheckErrors [bad errors]', tags=['async', 'unit'])
async def _(ctx=ctx, check=each(*_TRIALS['bad_errors'])):
    with raises(ZeroDivisionError):
        await check(ctx)


@test('Cooldown(delta={d}, max_tokens={m}) throttles successive calls')
async def _(ctx=ctx, d=each(1.0, 2.0, 0.5, 0.33), m=each(1.0, 1.0, 2.0, 3.33)):
    cd = Cooldown(d, max_tokens=m)

    assert cd.retry_after == 0

    for _ in range(int(m)):
        assert (await cd(ctx)) is True

    assert (await cd(ctx)) is False
    assert d >= cd.retry_after > 0
