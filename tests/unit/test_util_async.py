import concurrent.futures as fs
import functools as ft
import asyncio

from ward import test, each, raises

from hautomate.util.async_ import is_main_thread, determine_concurrency, Asyncable


def _dummy_fn():
    return 1


async def _dummy_afn():
    return 1


class _dummy_cls:
    def __call__(self):
        return 1


#  All items should be copied for tests. They all return 1
_NAME = ('lambda', 'sync_func', 'callable', 'async_func', 'partial', 'coroutine', 'non_callable')
_CONCURRENCY = ('safe_sync', 'potentially_unsafe_sync', 'potentially_unsafe_sync', 'async', 'async', 'coroutine', None)
_TRIAL = (lambda: 1, _dummy_fn, _dummy_cls(), _dummy_afn, ft.partial(_dummy_afn), _dummy_afn(), 1)


@test('is_main_thread identifies [non]-main threads', tags=['unit'])
def _():
    with fs.ThreadPoolExecutor() as ex:
        f = ex.submit(is_main_thread)
        r = f.result()

    assert is_main_thread() is True
    assert r is False


@test('determine_concurrency unwraps partial of {name}', tags=['unit'])
def _(name=each(*_NAME[:-2]), result=each(*_CONCURRENCY[:-2]), trial=each(*_TRIAL[:-2])):
    wrapped = ft.partial(trial)
    r = determine_concurrency(wrapped)
    assert r == result


@test('determine_concurrency handles all types of callables: {name} [{concurrency}]', tags=['unit'])
def _(name=each(*_NAME), concurrency=each(*_CONCURRENCY), trial=each(*_TRIAL)):
    try:
        r = determine_concurrency(trial)
    except Exception:
        with raises(TypeError):
            r = determine_concurrency(trial)
    else:
        r == concurrency


@test('Asyncable runs from main thread: name={name}, concurrency={concurrency}', tags=['async', 'unit'])
async def _(name=each(*_NAME[:-2]), concurrency=each(*_CONCURRENCY[:-2]), trial=each(*_TRIAL[:-2])):
    awt = Asyncable(trial)
    r = await awt()
    assert r == 1


@test('Asyncable runs from alternate thread: name={name}, concurrency={concurrency}', tags=['async', 'unit'])
async def _(name=each(*_NAME[:-2]), concurrency=each(*_CONCURRENCY[:-2]), trial=each(*_TRIAL[:-2])):
    loop = asyncio.get_event_loop()

    def _other_thread():
        awt = Asyncable(trial)
        return awt(loop=loop)

    with fs.ThreadPoolExecutor() as ex:
        f = ex.submit(_other_thread)

        # allow background task switching to happen
        while not f.done():
            await asyncio.sleep(0)

        assert f.result() == 1
