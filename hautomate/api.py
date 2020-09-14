import importlib
import logging
import pathlib
import inspect

from hautomate.util.async_ import safe_sync
from hautomate.context import Context
from hautomate.errors import HautoError
from hautomate.events import _EVT_INIT


_log = logging.getLogger(__name__)


def _is_api(obj) -> bool:
    """
    Determine if object in a module is an api.
    """
    if inspect.isclass(obj) and issubclass(obj, API):
        return True
    return False


class API:
    """

    """
    _hauto = None

    def __init__(self, hauto):
        self.hauto = hauto
        self._intents = []

        if hauto is not None:
            type(self)._hauto = hauto

    # @property
    # def intents(self):
    #     return self._intents

    # @intents.setter
    # def intents(self, intent):
    #     self._intents.append(intent)

    # def __str__(self):
    #     return f'<API.{self.name}>'

    # def __repr__(self):
    #     return str(self)


class APIRegistry:
    """

    """
    def __init__(self, hauto):
        self.hauto = hauto
        self._apis = {}

        self.hauto.bus.subscribe(_EVT_INIT, self._load_all_apis)

    @safe_sync
    def _load_all_apis(self, ctx: Context):
        """

        """
        # break the circular imports
        from hautomate.apis import trigger, moment

        # set up the built-in apis first
        cfg = self.hauto.config.api_configs.get('moment', None)
        data = cfg.dict() if cfg is not None else {}
        self._apis['moment'] = moment(self.hauto, **data)
        self._apis['trigger'] = trigger(self.hauto)

        for path in (pathlib.Path(__file__).parent / 'apis').iterdir():
            if (
                path.stem.startswith('__')
                or path.stem in ['trigger', 'moment']
                or path.is_file()
            ):
                continue

            # eg.    /apis/<homeassistant>/<homeassistant>.py
            module = importlib.import_module(f'hautomate.apis.{path.stem}')
            name, api_cls = next(iter(inspect.getmembers(module, _is_api)))

            try:
                cfg = self.hauto.config.api_configs[name]
            except KeyError:
                _log.info(f"couldn't find api configuration for '{name}', skipping")
                continue

            _log.info(f"setting up api '{name}'")
            name = cfg.pop('name', name)
            self._apis[name] = api_cls(self.hauto, **cfg.dict())

    def __getitem__(self, name: str) -> API:
        try:
            return self._apis[name]
        except KeyError:
            raise HautoError(f"api '{name}' does not exist")
