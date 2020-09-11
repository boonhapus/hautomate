from hautomate.app import App


class MyApp(App):
    """
    Dummy App!
    """
    def __init__(self, hauto, name, x):
        super().__init__(hauto, name=name)
        self.x = x

    # async def on_dummy_event(self, ctx):
    #     pass


def setup(hauto):
    apps = [
        MyApp(hauto=hauto, name='app1', x=1),
        MyApp(hauto, name='app2', x=2)
    ]
    return apps
