from hautomate.app import App


class MyApp(App):
    """
    Dummy App!
    """
    def __init__(self, hauto, name, x):
        super().__init__(hauto, name=name)
        self.x = x
