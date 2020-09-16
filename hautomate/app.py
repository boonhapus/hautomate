from typing import List
from types import ModuleType
import importlib
import asyncio
# import inspect
import logging
import uuid

from hautomate.util.async_ import safe_sync
from hautomate.context import Context
from hautomate.errors import HautoError
from hautomate.events import EVT_START, EVT_APP_LOAD, EVT_APP_UNLOAD


_log = logging.getLogger(__name__)


class App:
    """
    Base class for a User's entrypoint into HAutomate.

    Parameters
    ----------
    hauto : HAutomate
      hautomate!

    name : str = None
      an optional name for this instance of the app
      if a name is not given, one will be generated for the app in order
      to distinguish it from other instances.
    """
    def __init__(self, hauto, *, name: str=None):
        self._id = str(uuid.uuid4())[:8]
        self.hauto = hauto
        self.name = name or f'{self.__class__.__name__}_{self._id}'
    #     self._intents = []

    # @property
    # def intents(self) -> List['Intent']:
    #     """
    #     All intents that were created by this app.
    #     """
    #     return self._intents


class AppRegistry:
    """
    A registry and loader for all Apps living within HAutomate.

    The registry lives on the Hautomate instance and can be iterated
    over as if it were a collection. Additionally, Users can grab the
    names of all loaded apps or a specific app as if it were an
    attribute. The registry also has a load and unload function in order
    to create apps dynamically.
    """
    def __init__(self, hauto):
        self.hauto = hauto
        self.apps_dir = hauto.config.apps_dir
        self._apps = {}

        self.hauto.bus.subscribe(EVT_START, self._load_all_apps)

    @property
    def names(self) -> list:
        """
        Return an iterable of app-names.
        """
        return list(self._apps.keys())

    @safe_sync
    def _load_all_apps(self, ctx: Context) -> None:
        """
        An Intent which loads all Apps within the apps_dir.
        """
        for path in self.apps_dir.iterdir():
            if path.stem.startswith('_'):
                continue

            self.load_app(path.stem)

    def _load_app_module(self, app: str) -> ModuleType:
        """
        Load an app.py file.
        """
        if (self.apps_dir / app).is_dir():
            fp = self.apps_dir / app / f'{app}.py'
        else:
            fp = self.apps_dir / f'{app}.py'

        if not fp.exists():
            raise ImportError(f"app file '{app}' could not be found")

        app_spec = importlib.util.spec_from_file_location(fp.stem, fp)
        module = importlib.util.module_from_spec(app_spec)
        app_spec.loader.exec_module(module)
        return module

    def _register(self, name: str, app: App) -> None:
        """
        Register an app with name.
        """
        if name in self._apps:
            raise HautoError(f"app name '{name}' already exists!")

        self._apps[name] = app

        # register_listeners
        # for name, meth in inspect.getmembers(app, inspect.ismethod):
        #     if name.startswith('on_'):
        #         self.hauto.bus.subscribe(name[3:].upper(), meth)

        #     if hasattr(meth, '__intents__'):
        #         for intent in meth.__intents__:
        #             intent._bind(meth)
        #             self.hauto.bus.subscribe(intent.event, intent)

    def __iter__(self):
        return iter(self._apps.copy().values())

    def __len__(self):
        return len(self._apps.copy())

    def __getattr__(self, app_name: str) -> App:

        try:
            app = self._apps[app_name]
        except KeyError:
            try:
                self.load_app(app_name)
            except ImportError:
                raise HautoError(f"app '{app_name}' does not yet exist")

            app = self._apps.get(app_name, None)

        if app is None:
            raise HautoError(f"app '{app_name}' does not yet exist")

        setattr(self, app_name, app)
        return app

    def load_app(self, app_name: str) -> List[App]:
        """
        Load all apps based on its name.

        Apps can be simple python files which live under the apps_dir
        location, or may have their own directory by the same name. If
        a complex app exists this way, the entrypoint should follow the
        pattern /apps_dir/cool_app_name/cool_app_name.py . This
        structure allows for package-like apps to exist. Apps and
        directories preceeded by a single- or double- underscore will
        not be candidates for loading.
        """
        _log.info(f"loading app '{app_name}'")
        module = self._load_app_module(app_name)

        try:
            apps = module.setup(self.hauto)
        except AttributeError:
            _log.warning(f"couldn't find a setup function for '{app_name}'!")
            apps = []
        else:
            if isinstance(apps, App):
                apps = [apps]

        for app in apps:
            self._register(app.name, app)

            # TODO: decide if this should wait until children has finished
            coro = self.hauto.bus.fire(EVT_APP_LOAD, parent=self.hauto, app=app)
            asyncio.create_task(coro)

        return apps

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
            raise HautoError(f"app '{name}' is not yet loaded!")

        # try:
        #     app.__module__.teardown(self.hauto)
        # except AttributeError:
        #     pass

        # for intent in app.intents:
        #     intent.cancel()

        # TODO: decide if this should wait until children has finished
        coro = self.hauto.bus.fire(EVT_APP_UNLOAD, parent=self.hauto, app=app)
        asyncio.create_task(coro)
