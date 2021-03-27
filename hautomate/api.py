from typing import Callable
import functools as ft
import logging
import inspect

from hautomate.util.async_ import safe_sync, Asyncable
from hautomate.context import Context
from hautomate.errors import HautoError
from hautomate.events import _EVT_INIT
from hautomate.enums import CoreState


_log = logging.getLogger(__name__)


class API:
    """
    Base class for APIs.

    APIs operate much like Singletons. The main idea being that it's
    perfectly valid for a public API method to be called directly from
    the class. This allows the user to be able to reference the API as
    an import.

    ---

    from hautomate import App
    from hautomate.apis import trigger

    class MyCoolApp(App):

        @trigger.on('SOME_EVENT')
        def do_a_thing(ctx):
            trigger.wait_for('SOME_OTHER_EVENT')

    ---

    This would be a totally valid workflow.
    """
    subclasses = {}
    instances = {}

    def __init_subclass__(cls, **kwargs):
        cls.api_name = name = cls.__name__.lower()
        cls.subclasses[name] = cls
        super().__init_subclass__(**kwargs)

    def __init__(self, hauto):
        self._hauto = hauto
        self.intents = []

        cls = type(self)
        cls.instances[cls.api_name] = self

    @property
    def hauto(self):
        """
        The Hautomate instance.
        """
        return self._hauto

    async def fire(self, event: str, *, wait: str=None, **event_data):
        """
        Send a message over the event bus.

        Parameters
        ----------
        event : str
            name of the event to trigger Intents

        data : dict
            extra data to pass into matching Intents

        return_when : str, default = ALL_FIRED
            one of ALL_FIRED, FIRST_COMPLETED, FIRST_EXCEPTION, or ALL_COMPLETED
        """
        kwargs = {
            'event': event,
            'parent': self.name,
            'wait': wait,
            **event_data
        }
        return await self.hauto.bus.fire(**kwargs)


class APIRegistry:
    """
    A registry and loader for all APIs living within Hautomate.
    """
    def __init__(self, hauto):
        self.hauto = hauto
        self._apis = {}

        self.hauto.bus.subscribe(_EVT_INIT, self._load_all_apis)

    @safe_sync
    def _load_all_apis(self, ctx: Context):
        """
        An Intent which loads all APIs.
        """
        for name, api_cls in API.subclasses.items():
            try:
                cfg = self.hauto.config.api_configs[name]
            except KeyError:
                _log.info(f"couldn't find api configuration for '{name}', skipping")
                continue

            _log.info(f"setting up api '{name}'")
            data = cfg.dict() if cfg is not None else {}
            self._apis[name] = api = api_cls(self.hauto, **data)

            # register_listeners
            for name, meth in inspect.getmembers(api, inspect.ismethod):
                if name.startswith('on_'):
                    self.hauto.bus.subscribe(name[3:].upper(), meth)

    def __getattr__(self, name: str) -> API:
        try:
            return self._apis[name]
        except KeyError:
            raise HautoError(f"api '{name}' does not exist")


class public_method(Asyncable):
    """
    Wrapper for a public_method.

    This decorator simply grabs the instance that's already set up.
    """
    def __get__(self, instance: object, owner: API):
        if instance is None:
            instance = owner.instances[owner.api_name]

        # if it's safe_sync, happy to run this in the event loop directly
        if self.concurrency == 'safe_sync':
            injected = ft.partial(self.func, instance)
        else:
            injected = ft.partial(self.__call__, instance, loop=instance.hauto.loop)

        instance.__dict__[self.func.__name__] = injected
        return injected


class api_method:
    """
    Wrapper for an api method which returns an Intent.

    This class builds the machinery to allow api methods to be called
    both in a declarative fashion, or a more classical imperative one.
    The only two requirements the api's method (aka intent_factory)
    must follow are:

        1. provide an optional keyword argument "fn"
        2. return an Intent

    That's it!
    """
    def __init__(self, intent_factory: Callable):
        self.intent_factory = intent_factory
        self.api = None  # see __get__

    def __get__(self, instance: object, owner: API):
        if instance is None:
            instance = owner.instances[owner.api_name]

        # bind the api instance so we can later access
        # hauto.bus.subscribe for the resulting Intent
        self.api = instance
        wrapped = ft.partial(self.__call__, instance)
        instance.__dict__[self.intent_factory.__name__] = wrapped
        return wrapped

    def __decorated__(self, *a, **kw):
        *a, fn = a
        intent = self.intent_factory(*a, fn=fn, **kw)

        try:
            fn.__intents__.append(intent)
        except AttributeError:
            fn.__intents__ = [intent]

        return fn

    def __call__(self, *a, fn: Callable=None, subscribe: bool=True, **kw):
        # declarative context: user wants to do
        #
        # @some_intent_creator(*a, **kw)
        # def intended(ctx):
        #   ...
        #
        if fn is None:
            # Declarative should only happen during the pre-start phase, on _EVT_INIT.
            # If we're finding that users are calling the declarative version without
            # a fn keyword argument, then they've likely made a mistake.
            if self.api.hauto._state not in (CoreState.initialized, CoreState.starting):
                __qualname__ = f'{self.api.name}.{self.intent_factory.__name__}'
                _log.warning(
                    'detected declarative context after startup!\ndid you forget to '
                    'provide the fn keyword argument?'
                )
                raise TypeError(f"{__qualname__}() missing 1 required keyword-only argument: 'fn'")

            # NOTE:
            #   in the past, we stored the original *a as _original_a=a, and then
            #   handled the error in __decorated__. If we move the above error to
            #   a warning, we'll want to do something like that again.
            return ft.partial(self.__decorated__, *a, **kw)

        # imperative context: user wants to do
        #
        # def intended(ctx):
        #   ...
        #
        # intent = some_intent_creator(*a, fn=intended, **kw)
        #
        intent = self.intent_factory(*a, fn=fn, **kw)

        if subscribe:
            self.api.hauto.bus.subscribe(intent.event, intent)

        return intent
