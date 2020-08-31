from typing import Union
import itertools as it

import pendulum

from hautomate.intent import Intent
from hautomate import HAutomate


_context_id = it.count()


class Context:
    """
    Execution context under which an Intent is fired.

    Contexts hold a lot of relevant information as to why a specific intent was
    triggered.
    """
    def __init__(
        self,
        hauto: 'HAutomate',
        event: str,
        *,
        target: 'Intent',
        parent: Union['Intent', 'HAutomate'],
        when: int=0
    ):
        self._id = next(_context_id)
        self._hauto = hauto
        self.event = event
        self.target = target
        self.parent = parent
        self._when_ts = when
        self._created_ts = pendulum.now(tz='UTC').timestamp()

    @property
    def hauto(self):
        """
        Grab a reference to HAutomate.
        """
        return self._hauto

    @property
    def when(self) -> Union[pendulum.DateTime, None]:
        """
        Datetime when the Context describes.

        Typically, this is when the Intent fires.
        """
        if self._when_ts == 0:
            return None

        return pendulum.from_timestamp(self._when_ts)

    @property
    def created_at(self) -> pendulum.DateTime:
        """
        Datetime when the Context was created.
        """
        return pendulum.from_timestamp(self._created_ts, tz='UTC')#.in_timezone(self.hauto.timezone)
