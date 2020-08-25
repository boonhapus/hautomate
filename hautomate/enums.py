import enum


class CoreState(enum.Enum):
    """
    Represent the current state of HAutomate.
    """
    initialized = 'INITIALIZED'
    starting = 'STARTING'
    ready = 'READY'
    closing = 'CLOSING'
    stopped = 'STOPPED'
    finished = 'FINISHED'

    # def __str__(self) -> str:
    #     return self.value
