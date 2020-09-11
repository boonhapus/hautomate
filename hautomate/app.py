from typing import Dict
from types import ModuleType
import itertools as it
import importlib
import asyncio
import inspect
import logging
import pathlib
import sys

from hautomate.errors import HautoError
from hautomate.events import EVT_APP_LOAD, EVT_APP_UNLOAD


_log = logging.getLogger(__name__)
_intent_id = it.count()


class App:
    """
    """
    def __init__(self, hauto, *, name: str=None):
        self._id = next(_intent_id)
        self.hauto = hauto
        self.name = name or self._id  # TBD
        self._intents = []

    @property
    def intents(self):
        return self._intents


class AppRegistry:
    """
    """
    def __init__(self, hauto):
        self.hauto = hauto
        self.apps_dir = hauto.config.apps_dir
        self._apps = {}

    @staticmethod
    def _load_module_from_file(fp: pathlib.Path) -> ModuleType:
        app_spec = importlib.util.spec_from_file_location(fp.stem, fp)
        module = importlib.util.module_from_spec(app_spec)
        app_spec.loader.exec_module(module)
        return module

    @property
    def apps(self):
        """
        Return a copy of all the active apps.
        """
        return self._apps.copy()

    # Allow AppRegistry to behave as a dict-like object

    def __len__(self):
        return len(self._apps)

    def __iter__(self):
        return iter(self.apps.values())

    def __getitem__(self, key: str) -> App:
        try:
            app = self._apps[key]
        except KeyError:
            raise HautoError(f"app '{key}' has not been registered!")

        return app

    def items(self):
        """
        Return an iterable of tuple pairs, for app-name and app.
        """
        return self.apps.items()

    def names(self) -> iter:
        """
        Return an iterable of app-names.
        """
        return iter(self.apps.keys())

    keys = names
    values = __iter__

    #

    def _initial_load_apps(self):
        """
        On initial load, we'll search the app directory for all possible
        apps.

        NOTE: might need to hack this into being async with an asyncio.sleep(0) in each
              iteration of the iterdir loop.
        """
        for fp in self.apps_dir.iterdir():
            # ignore __init__.py, __pycache__/, etc
            if fp.stem.startswith('__'):
                continue

            if fp.is_dir():
                sys.path.append(fp.as_posix())
                # this is the convention to speak of
                # /apps/my_complex_app/my_complex_app.py
                fp = fp / f'{fp.stem}.py'

            self.load_app(fp)

    def _register(self, name: str, app: App) -> None:
        """
        Register an app.
        """
        # n_intents = 0
        self._apps[name] = app

        # register_listeners
        for name, meth in inspect.getmembers(app, inspect.ismethod):
            if name.startswith('on_'):
                self.hauto.bus.subscribe(name[3:].upper(), meth)
        #         n_intents += 1

            if hasattr(meth, '__intents__'):
                for intent in meth.__intents__:
                    intent._bind(meth)
                    self.hauto.bus.subscribe(intent.event, intent)
                    # n_intents += 1

        # app_qualname = f'{app.__module__}.{app.__class__.__name__}'

        # _log.info(
        #     f'registering {app.app_type}: {app_qualname} [{app.name}, '
        #     f'with {n_intents} intents]'
        # )

    def load_app(self, fp: pathlib.Path) -> None:
        """
        Add an app to the registry.
        """
        _log.debug(f'loading app from {fp}')

        try:
            module = self._load_module_from_file(fp)
        except FileNotFoundError:
            raise HautoError(f'{fp.name} does not exist')

        try:
            apps = module.setup(self.hauto)
        except AttributeError:
            _log.warning(f"couldn't find a setup function for {fp}!")
            return

        if isinstance(apps, App):
            apps = [apps]

        for app in apps:
            self._register(app.name, app)

            # TODO: decide if this should wait until children has finished
            coro = self.hauto.bus.fire(EVT_APP_LOAD, parent=self.hauto, app=app)
            asyncio.create_task(coro)

    def unload_app(self, name: str) -> None:
        """
        Remove an app from the registry.

        Removing an app from the registry will automatically cancel all
        intents created from it.
        """
        _log.info(f"unloading app '{name}'")

        try:
            app = self._apps.pop(name)
        except KeyError:
            raise HautoError(f"app '{name}' is not yet registered!")

        # try:
        #     app.__module__.teardown(self.hauto)
        # except AttributeError:
        #     pass

        for intent in app.intents:
            intent.cancel()

        # TODO: decide if this should wait until children has finished
        coro = self.hauto.bus.fire(EVT_APP_UNLOAD, parent=self.hauto, app=app)
        asyncio.create_task(coro)
