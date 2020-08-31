from ward import test, fixture
import pendulum

from hautomate.context import Context


@fixture(scope='module')
def now():
    return pendulum.now(tz='UTC').timestamp()


@fixture(scope='module')
def contexts(now=now):
    earlier = now - 7

    ctxs = [
        Context('HAuto', None, target='Intent', parent='ward.test', when=earlier + mod)
        for mod in range(10)
    ]

    return ctxs


@test('Contexts are never exactly alike')
def _(now=now):
    L = Context('HAuto', None, target='Intent', parent='ward.test')
    R = Context('HAuto', None, target='Intent', parent='ward.test')
    assert L.__dict__ != R.__dict__

    L = Context('HAuto', None, target='Intent', parent='ward.test', when=now)
    R = Context('HAuto', None, target='Intent', parent='ward.test', when=now)
    assert L.__dict__ != R.__dict__


@test('Context.when returns None or pendulum.DateTime')
def _(now=now):
    ctx = Context('HAuto', None, target='Intent', parent='ward.test')
    assert ctx.when is None

    ctx = Context('HAuto', None, target='Intent', parent='ward.test', when=now)
    assert isinstance(ctx.when, pendulum.DateTime) is True


@test('Context.created_at returns pendulum.DateTime')
def _(now=now):
    ctx = Context('HAuto', None, target='Intent', parent='ward.test')
    assert isinstance(ctx.created_at, pendulum.DateTime) is True