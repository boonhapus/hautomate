import pendulum

from hautomate.settings import Settings


class Config(Settings):
    """
    Validator to ensure proper Moment API configuration.

    Attributes
    ----------
    resolution : float = 1.0
      number of seconds between TIME_UPDATE events

    speed : float = 1.0
      factor at which time passes every iteration, default is 1.0 or realtime

    epoch : pendulum.DateTime = None
      start of the virtual clock, default is None, to mean no initial skew
    """
    resolution: float = 1.0
    speed: float = 1.0
    epoch: pendulum.DateTime = None
