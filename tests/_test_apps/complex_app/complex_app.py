import logging

from hautomate.apis import trigger
from hautomate.app import App


_log = logging.getLogger(__name__)


class MyApp(App):
    """
    Dummy App!
    """
    def __init__(self, hauto, x, *, name=None):
        super().__init__(hauto, name=name)
        self.x = x

    # async def on_dummy_event(self, ctx):
    #     pass

    # @trigger.on('DUMMY')
    # async def some_intent(self, ctx):
    #     _log.info('ayyyoooo')


def setup(hauto):
    return MyApp(hauto=hauto, x=1)
