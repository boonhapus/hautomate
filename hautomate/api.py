import importlib
import logging
import pathlib
import inspect

from hautomate.util.async_ import safe_sync
from hautomate.context import Context
from hautomate.events import _EVT_INIT


_log = logging.getLogger(__name__)


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

    def __init__(self, hauto):
        self.hauto = hauto
        self._apis = {}

        self.hauto.bus.subscribe(_EVT_INIT, self._load_all_apis)

    @safe_sync
    def _load_all_apis(self, ctx: Context):
        """
        # gather and register all APIs
        """
        for path in (pathlib.Path(__file__).parent / 'apis').iterdir():
            if not path.is_dir() or path.stem.startswith('__'):
                continue

            # eg.    /apis/<homeassistant>/<homeassistant>.py
            module = importlib.import_module(f'hautomate.apis.{path.stem}')

            # get all subclasses of API
            def _is_api(obj):
                if inspect.isclass(obj) and issubclass(obj, API):
                    return True
                return False

            name, api = next(iter(inspect.getmembers(module, _is_api)))
