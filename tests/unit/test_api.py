from ward import test

from hautomate import HAutomate

from tests.fixtures import cfg_hauto


@test('APIRegistry')
async def _(cfg=cfg_hauto):
    """ async because we call loop.create_task upon AppRegistry.load(app) """
    hauto = HAutomate(cfg)
    hauto.apis._load_all_apis(None)

    assert 1 == 2
