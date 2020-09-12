from hautomate.app import App


class MyApp(App):
    """
    Dummy App!
    """
    def __init__(self, hauto, x, *, name=None):
        super().__init__(hauto, name=name)
        self.x = x

    # async def on_dummy_event(self, ctx):
    #     pass


def setup(hauto):
    return MyApp(hauto=hauto, x=1)
