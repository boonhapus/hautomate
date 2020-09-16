import asyncio
import time

from ward import test, each
import pendulum

from hautomate.apis.moment.settings import Config as MomentConfig
from hautomate import HAutomate

from tests.fixtures import cfg_hauto


@test('APIRegistry autosetup runs on builtin apis')
def _(cfg=cfg_hauto):
    # overwrite any existing api configs
    cfg.api_configs = {}

    hauto = HAutomate(cfg)
    hauto.apis._load_all_apis(None)
    hauto.apis.trigger
    hauto.apis.moment

    # from hautomate.api import API
    # print(API._registry)
    # assert 1 == 2


@test('Moment API allows time travel: speed={speed}, epoch={epoch}')
async def _(
    cfg=cfg_hauto,
    speed=each(1.0, 2.0),
    epoch=each(None, pendulum.parse('1999/12/31 12:59:00'))
):
    # overwrite any existing api configs
    cfg.api_configs = {'moment': MomentConfig(speed=speed, epoch=epoch)}
    hauto = HAutomate(cfg)

    try:
        task = asyncio.create_task(hauto.start())
        coro = asyncio.shield(task)
        await asyncio.wait_for(coro, 0.1)
    except asyncio.TimeoutError:
        pass

    real_beg = time.perf_counter()
    virt_beg = hauto.now
    await asyncio.sleep(0.25)
    virt_end = hauto.now
    real_end = time.perf_counter()

    real_elapsed = real_end - real_beg
    virt_elapsed = (virt_end - virt_beg).total_seconds()

    assert round(virt_elapsed / speed, 2) == round(real_elapsed, 2)

    # cleanup
    task.cancel()
