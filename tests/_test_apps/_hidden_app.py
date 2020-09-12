from hautomate.app import App


class MyApp(App):
    """
    Dummy App!
    """
    def __init__(self, hauto, name, x):
        super().__init__(hauto, name=name)
        self.x = x

    async def on_dummy(self, ctx):
        pass


def setup(hauto):
    return MyApp(hauto, name='hidden', x=2)
