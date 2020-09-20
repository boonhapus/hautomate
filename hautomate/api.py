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
    def __init__(self, func: Callable):
        self.intent_factory = func
        self.api = None  # see __get__

    def __get__(self, instance, owner):
        if instance is None:
            instance = owner.instances[owner.name]

        # bind the api instance we'll need to .subscribe the resulting Intent
        self.api = instance
        wrapped = ft.partial(self.__call__, instance)
        instance.__dict__[self.intent_factory.__name__] = wrapped
        return wrapped

    def __decorated__(self, *a, **kw):
        *a, func = a

        if func is None or func is self.api:
            raise TypeError(f"{self.intent_factory.__qualname__}() missing 1 required keyword-only argument: 'func'")

        intent = self.intent_factory(*a, func=func, **kw)
        self.api.hauto.bus.subscribe(intent.event, intent)
        return intent

    def __call__(self, *a, func=None, **kw):
        """
        If func is provided, we'll skip down to creating an intent.
        If we're being used as a decorator (default: False)
        """
        if func is None:
            return ft.partial(self.__decorated__, *a, **kw)

        intent = self.intent_factory(*a, func=func, **kw)
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
