import itertools as it

import pendulum


_context_id = it.count()


class Context:

    def __init__(self, hauto, event, *, target, parent, when=0):
        self._id = next(_context_id)
        self._hauto = hauto
        self.event = event
        self.target = target
        self.parent = parent
        self._when_ts = when
        self._created_ts = pendulum.now(tz='UTC').timestamp()

    @property
    def when(self):
        if self._when_ts == 0:
            return None

        return pendulum.from_timestamp(self._when_ts)

    @property
    def created_at(self) -> pendulum.DateTime:
        return pendulum.from_timestamp(self._created_ts, tz='UTC')#.in_timezone(self.hauto.timezone)

    def __lt__(self, other) -> bool:
        return (self._when_ts, self._id) < (other._when_ts, other._id)
