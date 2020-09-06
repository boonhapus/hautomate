import asyncio
import random

from ward import test, each, raises, fixture
import pendulum

from hautomate.context import Context
from hautomate.errors import HautoException, CheckError
from hautomate.check import Check, Cooldown, Throttle, Debounce
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
        Throttle()
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


@test('cant instantiate Cooldown directly')
async def _():
    with raises(HautoException):
        Cooldown()


@test('{cd} throttles successive calls')
async def _(
    ctx=ctx,
    cd=each(
        Throttle(1.00, max_tokens=1.00),
        Throttle(2.00, max_tokens=1.00),
        Throttle(0.50, max_tokens=2.00),
        Throttle(0.33, max_tokens=3.33),
    )
):
    old_ctx = ctx.asdict()
    old_ctx.pop('when')

    d = cd._seconds
    m = cd._max_tokens
    assert cd.retry_after == 0

    tasks = []

    for _ in range(int(m)):
        ctx = Context(**old_ctx, when=pendulum.now(tz='UTC'))
        tasks.append(cd(ctx))

    r = await asyncio.gather(*tasks)
    assert all(r) is True

    ctx = Context(**old_ctx, when=pendulum.now(tz='UTC'))
    r = await cd(ctx)
    assert r is False

    assert d >= cd.retry_after > 0


@test('{cd} debounces initial calls within {cd.wait}s')
async def _(
    ctx=ctx,
    cd=each(
        Debounce(0.10, edge='LEADING'),
        Debounce(0.25, edge='LEADING'),
    )
):
    old_ctx = ctx.asdict()
    old_ctx.pop('when')

    beg = pendulum.now()

    ctx = Context(**old_ctx, when=pendulum.now(tz='UTC'))
    task = cd(ctx)
    await asyncio.sleep(0.05)

    r2 = await cd(ctx)
    elapsed = (pendulum.now() - beg).total_seconds()
    r1 = task.result()

    assert r1 is True
    assert r2 is False
    assert elapsed <= cd.wait

    # asyncio.sleep makes best effort to be right on the money, and will
    # release back to the event loop prior to that amount to account for
    # overhead. We add 1/100th of a second to ensure we actually wait
    # this long.
    await asyncio.sleep(cd.wait + .01)
    ctx = Context(**old_ctx, when=pendulum.now(tz='UTC'))
    r = await cd(ctx)
    assert r is True


@test('{cd} debounces successive calls for {cd.wait}s')
async def _(
    ctx=ctx,
    cd=each(
        Debounce(0.10, edge='TRAILING'),
        Debounce(0.25, edge='TRAILING')
    )
):
    old_ctx = ctx.asdict()
    old_ctx.pop('when')

    beg = pendulum.now()

    ctx = Context(**old_ctx, when=pendulum.now(tz='UTC'))
    task = cd(ctx)
    await asyncio.sleep(0.05)

    r2 = await cd(ctx)
    elapsed = (pendulum.now() - beg).total_seconds()
    r1 = task.result()

    assert r1 is False
    assert r2 is True
    assert elapsed >= cd.wait

    # asyncio.sleep makes best effort to be right on the money, and will
    # release back to the event loop prior to that amount to account for
    # overhead. We add 1/100th of a second to ensure we actually wait
    # this long.
    await asyncio.sleep(cd.wait + .01)
    ctx = Context(**old_ctx, when=pendulum.now(tz='UTC'))
    r = await cd(ctx)
    assert r is True
