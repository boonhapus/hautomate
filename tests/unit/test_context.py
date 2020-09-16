from ward import test, fixture
import pendulum

from hautomate.context import Context


@fixture(scope='module')
def now():
    return pendulum.now(tz='UTC')


@fixture(scope='module')
def contexts(now=now):
    earlier = now.subtract(seconds=7)

    ctxs = [
        Context('HAuto', None, event_data={}, target='Intent', when=earlier, parent='ward.test')
        for mod in range(10)
    ]

    return ctxs


@test('Contexts are never exactly alike', tags=['unit'])
def _(now=now):
    L = Context('HAuto', None, event_data={}, target='Intent', parent='ward.test', when=now)
    R = Context('HAuto', None, event_data={}, target='Intent', parent='ward.test', when=now)
    assert L.__dict__ != R.__dict__


@test('Context.when returns pendulum.DateTime', tags=['unit'])
def _(now=now):
    ctx = Context('HAuto', None, event_data={}, target='Intent', parent='ward.test', when=now)
    assert isinstance(ctx.when, pendulum.DateTime) is True


@test('Context.created_at returns pendulum.DateTime', tags=['unit'])
def _(now=now):
    ctx = Context('HAuto', None, event_data={}, target='Intent', parent='ward.test', when=now)
    assert isinstance(ctx.created_at, pendulum.DateTime) is True
