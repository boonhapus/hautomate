from typing import Callable
import functools as ft
import threading
import asyncio
import logging


_log = logging.getLogger(__name__)


def safe_sync(f: Callable) -> Callable:
    """
    Mark a func as safe to run within the event loop.
    """
    f.safe_sync = True
    return f


def is_main_thread() -> bool:
    """
    Check if we are in the main thread.
    """
    return threading.main_thread() == threading.current_thread()


def determine_concurrency(func: Callable) -> str:
    """
    Determine the concurrency paradigm to use, if any.
    """
    while isinstance(func, ft.partial):
        func = func.func

    if asyncio.iscoroutine(func):
        return 'coroutine'

    if not callable(func):
        raise TypeError('"{func}" is not a callable')

    if asyncio.iscoroutinefunction(func):
        return 'async'

    # Lambdas are meant to be short expressions, so it's USUALLY a safe bet that they're
    # not doing CPU- or IO-heavy operations.
    if hasattr(func, 'safe_sync') or getattr(func, '__name__', None) == '<lambda>':
        return 'safe_sync'

    return 'potentially_unsafe_sync'


class Asyncable:
    """
    Turn any callable into an async version of itself.

    Attributes
    ----------
    func : Callable
        callable to make asynchronous

    concurrency : str
        method of concurrency, must be one of the following:

          async - an asynchronous function
          safe_sync - a callback that doesn't do significant IO- or CPU-bound work
          potentially_unsafe_sync - a callback that might block the event loop
    """
    def __init__(self, func: Callable, *, concurrency: str=None):
        self.func = func
        self.concurrency = concurrency or determine_concurrency(func)

        if self.concurrency == 'coroutine':
            func.close()
            raise TypeError(
                f'a coroutine "{func}" was provided, try passing this directly to the '
                'event loop or supplying the underlying callable'
            )

    def __call_threadsafe__(self, main_loop: asyncio.AbstractEventLoop, *a, **kw):
        """
        Threadsafe version of __call__.

        The only time this method will be invoked is when synchronous
        code calls an Asyncable from another thread. This will not
        return an awaitable like __call__, but instead return the result
        of that awaitable instead.
        """
        if self.concurrency == 'safe_sync':
            async def _wrapped(func, *a, **kw):
                return func(*a, **kw)

            coro = _wrapped(self.func, *a, **kw)

        elif self.concurrency == 'potentially_unsafe_sync':
            # We're looking for a coroutine, so something like
            # loop.call_soon_threadsafe(loop.run_in_executor, ...) would not work in
            # this case (since you can't await a handle).
            async def _wrapped(func, loop):
                return await loop.run_in_executor(None, func)

            func = ft.partial(self.func, *a, **kw)
            coro = _wrapped(func, main_loop)

        else:
            coro = self.func(*a, **kw)

        return asyncio.run_coroutine_threadsafe(coro, main_loop).result()

    def __call__(self, *a, loop: asyncio.AbstractEventLoop=None, **kw):
        if not is_main_thread():
            return self.__call_threadsafe__(main_loop=loop, *a, **kw)

        loop = asyncio.get_event_loop()

        if self.concurrency == 'safe_sync':
            async def _wrapped(func, *a, **kw):
                return func(*a, **kw)

            coro = _wrapped(self.func, *a, **kw)
            awt = loop.create_task(coro)
        elif self.concurrency == 'potentially_unsafe_sync':
            fn = ft.partial(self.func, *a, **kw)
            awt = loop.run_in_executor(None, fn)
        else:
            coro = self.func(*a, **kw)
            awt = loop.create_task(coro)

        return awt
