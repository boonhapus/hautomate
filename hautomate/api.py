from typing import Callable
import functools as ft
import logging
import inspect

from hautomate.util.async_ import safe_sync
from hautomate.context import Context
from hautomate.errors import HautoError
from hautomate.events import _EVT_INIT


_log = logging.getLogger(__name__)


class api_method:
    """
    """
    def __init__(self, fn: Callable):
        self.intent_factory = fn
        self.api = None  # see __get__

    def __get__(self, instance, owner):
        if instance is None:
            instance = owner.instances[owner.name]

        # bind the api instance to pretend like we know if the user is calling
        # the decorated version appropriately, as well as access
        # hauto.bus.subscribe for the resulting Intent
        self.api = instance
        wrapped = ft.partial(self.__call__, instance)
        instance.__dict__[self.intent_factory.__name__] = wrapped
        return wrapped

    def __decorated__(self, *a, _original_a: dict, **kw):
        *a, fn = a

        # NOTE:
        #
        # this is the situation where a sync-User attempts to call the
        # declarative paradigm imperatively. It's not valid to do, so we're
        # going to log a warning and help them out.
        if tuple(a) != _original_a:
            factory = self.intent_factory.__qualname__
            fn_name = fn.__name__
            a_repr = kw_repr = ''

            if a[1:]:
                args = ', '.join(f'{_}' for _ in a[1:])
                a_repr = f'{args}, '

            if kw:
                kwgs = ', '.join(f'{k}={v}' for k, v in kw.items())
                kw_repr = f', {kwgs}'

            signature = f'{factory}({a_repr}fn={fn_name}{kw_repr})'

            _log.error(
                f"calling '{fn_name}' as if it were a decorator, if you're getting "
                f"unexpected results, maybe you meant:  {signature}"
            )
            raise TypeError(f"{self.intent_factory.__qualname__}() missing 1 required keyword-only argument: 'fn'")

        intent = self.intent_factory(*a, fn=fn, **kw)

        try:
            fn.__intents__.append(intent)
        except AttributeError:
            fn.__intents__ = [intent]

        return fn

    def __call__(self, *a, fn: Callable=None, **kw):
        # declarative context: user wants to do
        #
        # @some_intent_creator(*a, **kw)
        # def intended(ctx):
        #   ...
        #
        if fn is None:
            # NOTE:
            # could create a subclass for partial and impl __await__, and then
            # warn the user when they await on a ft.partial (aka improper use
            # of an api_method)
            #
            # NOTE:
            # store the originally supplied args to tell if the User is in the
            # correct context
            return ft.partial(self.__decorated__, *a, _original_a=a, **kw)

        # imperative context: user wants to do
        #
        # def intended(ctx):
        #   ...
        #
        # intent = some_intent_creator(*a, fn=intended, **kw)
        #
        intent = self.intent_factory(*a, fn=fn, **kw)
        self.api.hauto.bus.subscribe(intent.event, intent)
        return intent


class API:
    """
    Base class for APIs.
    """
    subclasses = {}
    instances = {}

    def __init_subclass__(cls, name: str=None, **kwargs):
        super().__init_subclass__(**kwargs)
        name = name or cls.__name__.lower()
        cls.subclasses[name] = cls
        cls.name = name

    def __init__(self, hauto):
        self._hauto = hauto
        self._intents = []

        cls = type(self)
        cls.instances[cls.name] = self
        cls._hauto = hauto

    @property
    def hauto(self):
        """
        The HAutomate instance.
        """
        return self._hauto

    # @property
    # def intents(self):
    #     return self._intents

    # @intents.setter
    # def intents(self, intent):
    #     self._intents.append(intent)

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

        Returns
        -------
        tasks_or_results : List[Union[Task, Any]]
        """
        kwargs = {
            'event': event,
            'parent': self.name,
            'wait': wait,
            **event_data
        }
        return await self.hauto.bus.fire(**kwargs)

    # def __str__(self):
    #     return f'<API.{self.name}>'

    # def __repr__(self):
    #     return str(self)


class APIRegistry:
    """
    A registry and loader for all APIs living within HAutomate.
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
            if name == 'trigger':
                cfg = None
            elif name == 'moment':
                cfg = self.hauto.config.api_configs.get('moment', None)
            else:
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
