from hautomate.app import App


class MyApp(App):
    """
    Dummy App!
    """
    def __init__(self, x):
        self.x = x

    def on_dummy_event(self, ctx):
        pass


def setup(hauto):
    apps = [
        MyApp(x=1),
        MyApp(x=2)
    ]
    return apps
