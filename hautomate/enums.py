import enum


class CoreState(enum.Enum):
    """
    Represent the current state of Hautomate.
    """
    initialized = 'INITIALIZED'
    starting = 'STARTING'
    ready = 'READY'
    closing = 'CLOSING'
    stopped = 'STOPPED'
    finished = 'FINISHED'


class IntentState(enum.Enum):
    """
    Represent the current state of an Intent.
    """
    initialized = 'INITIALIZED'
    ready = 'READY'
    paused = 'PAUSED'
    cancelled = 'CANCELLED'
