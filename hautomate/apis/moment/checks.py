from typing import Union
import datetime as dt
import asyncio

import pendulum

from hautomate.context import Context
from hautomate.check import Check


class MomentaryCheck(Check):
    """
    """
    def __init__(self, dt_or_time: Union[pendulum.DateTime, pendulum.Time]):
        super().__init__(priority=0)
        self.dt_or_time = dt_or_time

    async def __check__(self, ctx: Context) -> bool:
        moment = ctx.hauto.apis.moment
        soon = ctx.when.add(seconds=moment.resolution * moment.speed)

        try:
            self.dt_or_time.date()
        except AttributeError:
            # we're a Time
            dattim = dt.datetime.combine(ctx.when.date(), self.dt_or_time)
            cmp_dattim = pendulum.instance(dattim, tz='UTC')
        else:
            # we're a DateTime
            cmp_dattim = self.dt_or_time

        if cmp_dattim <= ctx.when:
            return True

        if cmp_dattim <= soon:
            sec = soon.timestamp() - cmp_dattim.timestamp()
            return await asyncio.sleep(sec, True)

        return False
