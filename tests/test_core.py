import threading
import asyncio

from ward import test

from hautomate import HAutomate

from tests.fixtures import cfg_hauto


@test('positive scenarios: HAutomate.run')
def _(cfg=cfg_hauto):
    hauto = HAutomate(cfg)

    # start up in a new thread
    threading.Thread(target=hauto.run, daemon=True).start()
    assert hauto._stopped.is_set() is False

    # grab our stop coro and submit it to the current event loop
    coro = hauto.stop()
    loop = asyncio.get_event_loop()
    f = asyncio.run_coroutine_threadsafe(coro, loop)

    # wait for the coroutine to finish
    f.result()
    assert hauto._stopped.is_set() is True
