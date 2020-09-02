from typing import Union
import itertools as it

import pendulum


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
        when: pendulum.DateTime,
        parent: Union['Intent', 'HAutomate']
    ):
        self._id = next(_context_id)
        self._hauto = hauto
        self.event = event
        self.target = target
        self.parent = parent
        self._when_ts = when.in_timezone('UTC').timestamp()
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
        return pendulum.from_timestamp(self._when_ts, tz='UTC')#.in_timezone(self.hauto.config.timezone)

    @property
    def created_at(self) -> pendulum.DateTime:
        """
        Datetime when the Context was created.
        """
        return pendulum.from_timestamp(self._created_ts, tz='UTC')#.in_timezone(self.hauto.config.timezone)
