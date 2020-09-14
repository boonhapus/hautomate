import time

from ward import test

from hautomate import HAutomate

from tests.fixtures import cfg_hauto


@test('APIRegistry autosetup runs on builtin apis')
def _(cfg=cfg_hauto):
    # overwrite any existing api configs
    cfg.api_configs = {}

    hauto = HAutomate(cfg)
    hauto.apis._load_all_apis(None)
    hauto.apis['trigger']
    hauto.apis['moment']


# @test('Moment API allows time travel: rate={rate}, epoch={epoch}')
# async def _(cfg=cfg_hauto, rate=each(), epoch=each(), end=each()):
#     # overwrite any existing api configs
#     cfg.api_configs = {
#         'moment': {
#             'rate': rate,
#             'epoch': epoch
#         }
#     }

#     hauto = HAutomate(cfg)
#     # need to start
#     hauto.start()
#     hauto.apis._load_all_apis(None)

#     real_beg = time.perf_counter()
#     virt_beg = hauto.now
#     # sleep 1.0s
#     real_end = time.perf_counter()
#     virt_end = hauto.now

#     real_elapsed = time.perf_counter() - real_beg
#     virt_elapsed = hauto.now - virt_beg

#     assert real_elapsed == 1.0
#     assert virt_elapsed == 
#     assert virt_end == end
